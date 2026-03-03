# Note: easier to work with the gpkgs
# ogrinfo --config SQLITE_LIST_ALL_TABLES yes "ABSOLUTE_PATH_TO_.idbm"
# ogr2ogr -f "GPKG" "SAVE_TO.gpkg" "ABSOLUTE_PATH_TO_.idbm"
# 

# Read:
# https://trac.osgeo.org/gdal/ticket/6575
# https://gdal.org/programs/ogr2ogr.html

# SWMM specs. SEE MANUAL PAGE 330
#         [TITLE] project title
#         [OPTIONS] analysis options
#         [REPORT] output reporting instructions
#         [FILES] interface file options
#         [RAINGAGES] rain gage information
#         [EVAPORATION] evaporation data
#         [TEMPERATURE] air temperature and snow melt data
#         [ADJUSTMENTS] monthly adjustments applied to climate variables325
#         [SUBCATCHMENTS] basic subcatchment information
#         [SUBAREAS] subcatchment impervious/pervious subarea data
#         [INFILTRATION] subcatchment infiltration parameters
#         [LID_CONTROLS] low impact development control information
#         [LID_USAGE] assignment of LID controls to subcatchments
#         [AQUIFERS] groundwater aquifer parameters
#         [GROUNDWATER] subcatchment groundwater parameters
#         [GWF] groundwater flow expressions
#         [SNOWPACKS] subcatchment snow pack parameters
#         [JUNCTIONS] junction node information
#         [OUTFALLS] outfall node information
#         [DIVIDERS] flow divider node information
#         [STORAGE] storage node information
#         [CONDUITS] conduit link information
#         [PUMPS] pump link information
#         [ORIFICES] orifice link information
#         [WEIRS] weir link information
#         [OUTLETS] outlet link information
#         [XSECTIONS] conduit, orifice, and weir cross-section geometry
#         [TRANSECTS] transect geometry for conduits with irregular cross-sections
#         [STREETS] cross-section geometry for street conduits
#         [INLETS] design data for storm drain inlets
#         [INLET_USAGE] assignment of inlets to street and channel conduits
#         [LOSSES] conduit entrance/exit losses and flap valves
#         [CONTROLS] rules that control pump and regulator operation
#         [POLLUTANTS] pollutant information
#         [LANDUSES] land use categories
#         [COVERAGES] assignment of land uses to subcatchments
#         [LOADINGS] initial pollutant loads on subcatchments
#         [BUILDUP] buildup functions for pollutants and land uses
#         [WASHOFF] washoff functions for pollutants and land uses
#         [TREATMENT] pollutant removal functions at conveyance system nodes326
#         [INFLOWS] external hydrograph/pollutograph inflow at nodes
#         [DWF] baseline dry weather sanitary inflow at nodes
#         [RDII] rainfall-dependent I/I information at nodes
#         [HYDROGRAPHS] unit hydrograph data used to construct RDII inflows
#         [CURVES] x-y tabular data referenced in other sections
#         [TIMESERIES] time series data referenced in other sections
#         [PATTERNS] periodic multipliers referenced in other sections
#         [MAP] X,Y coordinates of the map’s bounding rectangle
#         [POLYGONS] X,Y coordinates for each vertex of subcatchment polygons
#         [COORDINATES] X,Y coordinates for nodes
#         [VERTICES] X,Y coordinates for each interior vertex of polyline links
#         [LABELS] X,Y coordinates and text of labels
#         [SYMBOLS] X,Y coordinates for rain gages
#         [BACKDROP] X,Y coordinates of the bounding rectangle and file name of the backdrop image.

import math
from typing import Callable
from tqdm import tqdm
import pandas
import sqlite3
import os

from SWMMObjects import (SWMMConfigObject, Auslass, Schacht, SpeicherSchacht, PumpHextran, WeirHextran, Curve,
                   CONDUITS,COORDINATES, WEIRS, XSECTIONS, CONTROLS, RULES, OUTFALLS, STORAGE, SUBCATCHMENTS, SUBAREAS,
                     INFILTRATION, Polygons, STORAGE, OUTFALLS, PUMPS,
)

import logging

def prandtl_to_manning(prandtl : float, **kwargs) -> float:
    """
    TODO
    Converts the prandlt-colebrook Rauigkeitbeiwert into a manning N
    """
    logging.warning(f"WARNING! Prandtl to manning only half implemented only for 1.5 mm. Current Value: {prandtl}")
    return prandtl * 0.0087



class SQLitetoSWMM:
    """
    This class will take a sqlite_path with the idbm format and convert it into a valid SWMM inp file.
    """
    class_list = [Auslass, Schacht, SpeicherSchacht, PumpHextran, WeirHextran, Curve,
                   CONDUITS,COORDINATES, WEIRS, XSECTIONS, CONTROLS, OUTFALLS, STORAGE, SUBCATCHMENTS, SUBAREAS, INFILTRATION, Polygons ]
    
    class_list_swmm = [STORAGE, OUTFALLS, PUMPS,
                        CONDUITS, WEIRS,  SUBCATCHMENTS, SUBAREAS, INFILTRATION, Polygons, XSECTIONS, Curve,  COORDINATES, CONTROLS,  ]
    
    GEOMETRY_FIELD = "TextGeometry"
    
    def __init__(self, sqlite_path : str, swmm_path : str, spatialite_dll_path  :str,):
        """
        swmm_path should end in .inp
        """
        self.sqlite_path = sqlite_path
        self.swmm_path = swmm_path
        self.spatialite_dll_path = spatialite_dll_path
        
        # Create one connection and load SpatiaLite once
        self.connection = sqlite3.connect(self.sqlite_path)
        try:
            self.connection.enable_load_extension(True)
            self.connection.load_extension(self.spatialite_dll_path)
        except sqlite3.OperationalError as e:
            logging.error(f"Failed to load SpatiaLite extension: {e}")
            raise

        
    
    def convert(self, headers : list[str] = [], write : bool = False, object_collection = None, **kwargs):
        """
        Transforms the specified idbm into an swmm .inp file
        individual_regenschreiber : requires the function assign_regenschreiber partially initialized

        """
        if not object_collection:
            object_collection = self.object_extraction(**kwargs)
        text = ""

        text += self.get_OPTIONS()

        classes : list[SWMMConfigObject] = self.class_list_swmm
        for cl in classes:
            text += cl.header()
            for item in object_collection:
                if issubclass(item.__class__, cl): # type: ignore
                    text += item.print()
        
        # text = self.get_inhalt(headers = headers)
        #write it
        if write:
            with open(self.swmm_path, "w") as f:
                f.write(text)

        return text
    
    def object_extraction(self, **kwargs) -> list[SWMMConfigObject]:
        """
        Converts the sql objects into python classes, so that we can later dump them into swmm
        individual_regenschreiber : requires the function assign_regenschreiber partially initialized
        """
        #TODO maybe jut execute everything that sarts with generate_
        collection = []
        functions = [
                    self.generate_conduits,
                    self.generate_sonderprofile,
                    self.generate_schacht,
                    self.generate_speicherschacht,
                    self.generate_auslass,
                    self.generate_pumpe,
                    self.generate_weirs,
                    self.generate_xsections,
                    self.generate_subcatchments,
        ]

        for f in tqdm(functions):
            collection.extend(f(**kwargs))
        return collection

    def get_input_nodes(self) -> pandas.DataFrame:
        """
        Returns all the Schacht whether they are Speicher or not
        """
        df_schacht = get_table(table_name = "Schacht", connection=self.connection)
        df_speicherschacht = get_table(table_name = "Speicherschacht", connection=self.connection)
        df_nodes = pandas.concat([df_schacht, df_speicherschacht])
        return df_nodes
        

    @staticmethod
    def split_point_geometry(text_geometry : str) -> tuple[float,float]:
        """
        Splits the point geom text
        """
        x, y = text_geometry[6:-1].split(" ")
        return float(x), float(y)

    @staticmethod
    def convert_pct_neigung(neigungsklasse : int) -> float:
        """
        The Neigungsklasse in Hextran are given by:
          1: less than 1%
          2: between 1 and 4%
            3: between 4-10%
            4: between 10-14%
            5: > 14%
            #TODO what does 5 actually mean...    
        """
        if neigungsklasse == 1: return 0.5
        elif neigungsklasse == 2: return 2.5
        elif neigungsklasse == 3: return 7
        elif neigungsklasse == 4: return 12
        elif neigungsklasse == 5: return 15
        else:
            raise ValueError("Not Implemented!!")

    def generate_conduits(self, **kwargs):
        #Conduits
        col = []
        table = get_table(table_name = "Rohr", connection=self.connection)
        for index, serie in table.iterrows():
            name = serie["Name"]
            fromnode = serie["SchachtOben"]
            tonode = serie["SchachtUnten"]
            length = serie["Laenge"]
            roughness_prandltcolebrook = serie["Rauigkeitsbeiwert"] #This is Prandtl-Colebrook Kst, we need manning n
            roughness = prandtl_to_manning(prandtl=roughness_prandltcolebrook)
            InOffset = serie["SohlhoeheOben"]
            OutOffset = serie["SohlhoeheUnten"]
            InitFlow = 0
            MaxFlow = 0.0#serie["DurchflussVollfuellung"] #LEFT OUT 

            conduit = CONDUITS(name = name, fromnode = fromnode, tonode = tonode,
                                length = length, roughness=roughness,
                                    InOffset=InOffset, OutOffset=OutOffset, InitFlow=InitFlow, MaxFlow=MaxFlow)
            col.append(conduit)
        return col

                
    def generate_xsections(self, **kwargs):
        #Conduits XSECTIONS
        col = []

        table = get_table(table_name = "Rohr", connection=self.connection)

        filling = {k:"0" for k in ["Geometrie1","Geometrie2","Geometrie3","Geometrie4"]}
        table.fillna(filling, inplace = True)
        for index, serie in table.iterrows():
            name = serie["Name"]
            shape = XSECTIONS.get_shape(str(serie["Profiltyp"]))
            Geom1 = serie["Geometrie1"]
            Geom2 = serie["Geometrie2"]
            if shape == "CUSTOM": Geom2 = serie["Sonderprofilbezeichnung"] #It will be automatically calculated
            Geom3 = serie["Geometrie3"]
            Geom4 = serie["Geometrie4"]
            Barrels = 1

            xsection = XSECTIONS(name = name, shape = shape, geom1 = Geom1, geom2 = Geom2, geom3 = Geom3, geom4 = Geom4, barrels = Barrels)

            col.append(xsection)
        return col


    def generate_sonderprofile(self, **kwargs):
        """Creates the curves section
        Höhe und breite from the lowest point. Scales at 1 meter, so in SWMM the values are depth/maxdepth and height/maxheight
        Example:
        [CURVES]
        ;;Name           Type       X-Value    Y-Value   
        ;;-------------- ---------- ---------- ----------
        ;700desc
        700              Shape      0          .0001     
        700                         0.0575     0.5599    
        700                         0.0948     0.7798    
        700                         0.1422     0.8898    
        ;
        ;600desc
        600              Shape      0          0         
        600                         0.04       0.465     
        600                         0.08       0.643 """
        #TODO So far its for GESCHLOSSEN
        #TODO OMIT THE DESCRIPTION
        col = []

        sonderprofiles = get_table(table_name = "Sonderprofil", connection=self.connection)
        tabelleninhalte = get_table(table_name = "Tabelleninhalte", connection=self.connection)
        for index, serie in sonderprofiles.iterrows():
            name = serie["Name"]
            #TODO: Description ;700desc...

            id = serie["Id"] #This is the ID that is used for the TabellenInhalte
            sub_table = tabelleninhalte[tabelleninhalte["Id"] == id]
            sub_table.sort_values("Reihenfolge", inplace = True)

            höhe = sub_table["KeyWert"].values.tolist()
            fläche = sub_table["Wert"].values.tolist()
            curve = Curve(name = name, Type = "Shape", x = höhe, y = fläche)
            col.append(curve)
        return col



    def generate_schacht(self, **kwargs):
    #Schacht. TODO make these information into objects and then export as its getting messy
        col = []

        table = get_table(table_name = "Schacht", connection=self.connection)
        table["MAXDEPTH"] = table["Deckelhoehe"]- table["Sohlhoehe"]
        #TODO what is Scheitelhoehe?
        for index, serie in table.iterrows():
            name = serie["Name"]
            curve = name
            elevation = str(serie["Sohlhoehe"])
            maxdepth = str(serie["MAXDEPTH"])
            diameter = serie["Durchmesser"]/1000

            planungsstatus = serie["Planungsstatus"] # if 3 = fiktiv, functional of 0

            x, y = serie[self.GEOMETRY_FIELD][6:-1].split(" ")
            area = (diameter/2)**2 * math.pi
            curve = Curve(name = name, Type = "Storage", x = [0, maxdepth], y = [area, area])
            schacht = Schacht(name = name, elevation = elevation, maxdepth = maxdepth, curve = curve)
            coords = COORDINATES(name = name, x = x, y = y)
            
            
            col.append(curve)
            col.append(schacht)
            col.append(coords)
        return col

    def generate_speicherschacht(self, **kwargs):
        #Storage schacht
        col = []
        table = get_table(table_name = "Speicherschacht", connection=self.connection)
        geometry_curves = get_table(table_name = "Tabelleninhalte", connection=self.connection)
        #TODO: Assumed Art is tabellarisch
        table["MAXDEPTH"] = table["HoeheVollfuellung"]- table["Sohlhoehe"]
        for index, serie in table.iterrows():
            name = serie["Name"]
            id = serie["Id"]
            elevation = serie["Sohlhoehe"]
            maxdepth = serie["MAXDEPTH"] 



            geometry = geometry_curves[geometry_curves["Id"] == id]
            geometry.sort_values("Reihenfolge", inplace = True)
            höhe = geometry["KeyWert"].values.tolist()
            fläche = geometry["Wert"].values.tolist()

            x, y = serie[self.GEOMETRY_FIELD][6:-1].split(" ")

            curve = Curve(name = name, Type = "Storage", x = höhe, y = fläche)
            coords = COORDINATES(name = name, x = x, y = y)

            speicherschacht = SpeicherSchacht(name = name, elevation = elevation, maxdepth = maxdepth, curve = curve)

            
            col.append(speicherschacht)
            col.append(curve)
            col.append(coords)
        return col

    def generate_auslass(self, **kwargs):
        #Auslass,
        col = []
        table = get_table(table_name = "Auslass", connection=self.connection)
        for index, serie in table.iterrows():
            name = serie["Name"]
            elevation = serie["Sohlhoehe"]
            auslass = Auslass(name = name, elevation = elevation)

            x, y = serie[self.GEOMETRY_FIELD][6:-1].split(" ")
            coords = COORDINATES(name = name, x = x, y = y) 

        
            col.append(auslass)
            col.append(coords)
        return col
                
        

        
    def generate_weirs(self, **kwargs):
        #Wehr
        col = []
        table = get_table(table_name = "Wehr", connection=self.connection)
        for index, serie in table.iterrows():
            name = serie["Name"]
            fromnode = serie["SchachtOben"]
            tonode = serie["SchachtUnten"]

            height = serie["Geometrie1"] # Öffnungsweite
            laenge = serie["Geometrie2"]
            geometrie = "RECT_OPEN" #TODO
            
            baseelevation = serie["Schwellenhoehe"] #Height of the CrestH

            Type = WeirHextran.get_profiltyp(typ = serie["Profiltyp"])
            Qcoeff = serie["Ueberfallbeiwert"]

            weir = WeirHextran(name = name, fromnode = fromnode, tonode = tonode, Type = Type, CrestHt = baseelevation, Qcoeff=Qcoeff)
            xsection = XSECTIONS(name = name, shape = geometrie, geom1 = height, geom2 = laenge, geom3 = 0, geom4 = 0)

            
            col.append(weir)
            col.append(xsection)
        return col

    def generate_pumpe(self, **kwargs):
        #Pumpe
        col = []
        table = get_table(table_name = "Pumpe", connection=self.connection)
        subpumps = get_table(table_name = "Tabelleninhalte", connection = self.connection)
        for index, serie in table.iterrows():
            name = serie["Name"]
            typ = str(serie["Typ"])

            #TODO HACK: for now we will assume that all pumps are Schaltung
            if typ != "2": raise ValueError("Pumpe: Pumpetyp not implemented yet!!")
            
            #These Values are shared for all subpumps
            SchachtOben = serie["SchachtOben"]
            SchachtUnten = serie["SchachtUnten"]
            
            #Get all subpumps
            id_anschalten = serie["Id"] #This is the ID that is used for the TabellenInhalte
            anschalten_values = subpumps[subpumps["Id"] == id_anschalten]
            anschalten_values.sort_values("Reihenfolge", inplace = True)
            ansch_m : list = anschalten_values["KeyWert"].values.tolist()
            leistungen : list = anschalten_values["Wert"].values.tolist()

            id_ausschalten = serie["TabelleRunterId"] #This is the ID that is used for the TabellenInhalte
            ausschalten_values = subpumps[subpumps["Id"] == id_ausschalten]
            ausschalten_values.sort_values("Reihenfolge", inplace = True)
            aussch_m : list = ausschalten_values["KeyWert"].values.tolist()


            sub_table = list(zip(ansch_m, aussch_m, leistungen))
            num_pumps = len(sub_table)
            

            #For each subpump, create in SWMM a new PUMP and a new CURVE
            for index_sp, (an, aus, leistung) in enumerate(sub_table):
                anschalten = an
                abschalten = aus
                #Leistung in cbm - important to check units.
                subpump_name = f"PUMP_{name}_{index_sp+1}of{num_pumps}"

                #RULES
                controls = (
                    f"RULE {subpump_name}_LEVELSSTOP\n"
                    f"IF NODE {SchachtOben} HEAD <= {abschalten} \n"
                    f"THEN PUMP {subpump_name} STATUS = OFF\n"
                    "PRIORITY 1\n"

                    f"RULE {subpump_name}_LEVELSSTART\n"
                    f"IF NODE {SchachtOben} HEAD > {anschalten}\n" 
                    f"THEN PUMP {subpump_name} STATUS = ON\n"
                    "\n"

                    
                )

                curve = Curve(name = subpump_name, Type = "Pump5", x = [0.0], y = [leistung])
                pump = PumpHextran(name = subpump_name, fromnode = SchachtOben, tonode = SchachtUnten, curve = curve)                       
                rules = RULES(multiline_text = controls)

                col.append(curve)
                col.append(pump)
                col.append(rules)
        return col
    

    def generate_subcatchments(self, individual_regenschreiber : Callable[[pandas.Series], int]|None = None, **kwargs):
        """
        Extracts the subcatchments from the Flaeche layer
        and the table from AbflussParameter
        individual_regenschreiber is a function
        """
        col = []

        df_flaeche = get_table(table_name = "Flaeche", connection=self.connection)
        df_param = get_table(table_name = "AbflussParameter", connection=self.connection)
        df_rohr = get_table(table_name = "Rohr", connection=self.connection)

        df_nodes = self.get_input_nodes()

        for index, serie in df_flaeche.iterrows():
            #Each Area is independent from the others
            name = serie["Name"]

            #Regenschreiber. Does this subcatchment even exist?
            regenschreiber : int = serie["Regenschreiber"]
            if individual_regenschreiber is not None:
                regenschreiber = individual_regenschreiber(serie)
            if regenschreiber is None:
                logging.info(f"Flaeche: {name} has no Regenschreiber and is discarded...")
                continue

            area_ha = serie["Groesse"]
            neigungsklasse = serie["Neigungsklasse"]
            slope = self.convert_pct_neigung(neigungsklasse) # of 100

            geometry = serie[self.GEOMETRY_FIELD]#Missing
            if geometry is not None: raise ValueError(f"Flaeche: {name} -> Geometry for this not implemented yet!! Check your tables")


            #Find the Parameters:
            parameter_id = serie["ParametersatzRef"]                
            parameter_row = df_param.query("Id == @parameter_id").iloc[0,:]

            #Find the Schacht upstream of the Rohr
            haltungref = serie["HaltungRef"]
            if math.isnan(haltungref): 
                logging.info(f"Flaeche: {name} has no HaltungRef and is discarded...")
                continue
            rohr = df_rohr.query("Id == @haltungref").iloc[0,:]

            ref_node = rohr["SchachtObenRef"] #This is actually a dataframe or a series depending on what happens
            schacht = df_nodes.query("Id == @ref_node").iloc[0,:]

            node_name = schacht["Name"]
            schacht_geom = schacht[self.GEOMETRY_FIELD]
            x, y = self.split_point_geometry(text_geometry = schacht_geom)
            
            pct_imperv = parameter_row["AbflussbeiwertAnfang"]*100 #TODO HACK

            subarea = SUBAREAS(subcatchment_name=name, RouteTo = "PERVIOUS", )
            width = area_ha**0.5 * 100 #TODO HACK

            

            subcatchment = SUBCATCHMENTS(name = name, raingage_name = str(regenschreiber), #HACK
                                            width = width, pct_slope = slope,
                                            outlet = node_name, area = area_ha, pct_imperv=pct_imperv)
            infiltr = INFILTRATION(subcatchment_name = name)
            polygon = Polygons(subcatchment_name = name, x = [x], y = [y]) #two points only for now


            col.extend([subarea, subcatchment, infiltr, polygon])
        return col

    def get_OPTIONS(self, **kwargs):
        """
        Gets the options text. VERY IMPORTANT to have the CMS value here
        #TODO
        [OPTIONS]
        ;;Option             Value
        FLOW_UNITS           CMS
        """

        header = ("[OPTIONS]\n"
                ";;Option             Value\n"
                "INFILTRATION         HORTON\n"
                "FLOW_ROUTING         DYNWAVE\n"
                "LINK_OFFSETS         ELEVATION\n"
                "FLOW_UNITS           CMS\n"
                "START_DATE           04/05/2023\n"
                "START_TIME           00:00:00\n"
                "REPORT_START_DATE    04/05/2023\n"
                "REPORT_START_TIME    00:00:00\n"
                "END_DATE             04/06/2023\n"
                "END_TIME             00:00:00\n"
                "THREADS              4\n"
                )
        return header
    

    
    

def connect(sqlite_path : str, spatialite_path)->sqlite3.Connection:
    con = sqlite3.connect(sqlite_path)
    #We need to enable SpatiaLite
    con.enable_load_extension(True) #This wont work if the particular sqlite version hasnt been compiled for this.
    con.load_extension(spatialite_path)
    return con

def get_table(table_name : str, connection: sqlite3.Connection) -> pandas.DataFrame:
    """
    Returns a table with the geometry as WKT
    """
    with connection as con:
        cur = con.cursor()
        columns = [i[1] for i in cur.execute(f'PRAGMA table_info({table_name})')]
        if "Geometry" in columns:
            # query = f"SELECT {table_name}.*, AsText({table_name}.Geometry) from {table_name}"
            query = f"SELECT {table_name}.*, AsText({table_name}.Geometry) as {SQLitetoSWMM.GEOMETRY_FIELD} from {table_name}"
        else:
            query = f"SELECT {table_name}.* from {table_name}"   

        table = pandas.read_sql_query(query , con)
        cur.close() 
        return table

def sqlite_dump(sqlite_path : str, export_folder : str, spatialite_dll_path : str):
    """
    Hextran files are actually Sqlite databases
    Dumps all the tables to a csv
    """

    with connect(sqlite_path, spatialite_dll_path) as con:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        for table_name in tables:
            table_name = table_name[0]
            try:
                #check columns
                columns = [i[1] for i in cur.execute(f'PRAGMA table_info({table_name})')]
                if "Geometry" in columns:
                    query = f"SELECT {table_name}.*, AsText({table_name}.Geometry) from {table_name}"
                else:
                    query = f"SELECT {table_name}.* from {table_name}"    
                table = pandas.read_sql_query(query , con)
                table.to_csv(os.path.join(export_folder, table_name + '.csv'), index_label='index')
            except Exception as e:
                logging.error(table_name, e)
        cur.close()


def assign_regenschreiber(item : pandas.Series, df : pandas.DataFrame|None) -> int:
    """
    We need a Dataframe with the regenschreiber stations.
    The item (subcatchment) must contain the subcatchment id "SCID" that will be related with the regenschreiber.
    The dataframe must contain the columns "SCID" and "RegenschreiberID", and the item series should have an "Id" field.
    """
    if df is None: return 1
    id = item["Id"]
    query = df.query("SCID == @id")
    if query.empty : return 1
    result = query.iloc[0,:]
    rs : int = int(result["RegenschreiberID"])
    logging.info(f"Regenschreiber pair id/rs: {id}, {rs}")
    return rs

