"""
Improvised intermediary items for the conversion of objects into swmm

"""

from dataclasses import dataclass, field
import logging


@dataclass(kw_only=True)
class SWMMConfigObject:

    @staticmethod
    def header() -> str: 
        raise ValueError("Not impemented!!")

    def print(self) -> str:
        raise ValueError("Not impemented!!")


@dataclass(kw_only=True)
class Curve(SWMMConfigObject):
    name : str
    Type : str #Storage, Pump1, Pump5, Shape, etc
    x : list[float]
    y : list[float]

    def __post_init__(self):
        if not isinstance(self.x, list): self.x = [self.x]
        if not isinstance(self.y, list): self.y = [self.y]

    @staticmethod
    def header ():
        curve_header = ("[CURVES]\n"
                ";;Name           Type       X-Value    Y-Value  \n" 
                ";;-------------- ---------- ---------- ----------\n"
            

        )
        return curve_header

    def print(self):
        line = ""
        xy = zip(self.x, self.y)
        for i, (x, y) in enumerate(xy):
            if i == 0:
                line += f"{self.name}           {self.Type}    {x}          {y}        \n"
            else:
                line += f"{self.name}                          {x}          {y}        \n"
        line += ";\n"
        return line


@dataclass(kw_only=True)
class STORAGE(SWMMConfigObject):
    #superclass so that we later can "if its storage..."
    name : str
    elevation : float
    maxdepth : float
    initdepth : float
    shape : str 
    curve : Curve
    surdepth : float
    fevap : float
    psi : float
    ksat : float
    IMD : float

    @staticmethod
    def header():
        header = ("[STORAGE]\n"
                    ";;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Type/Params            SurDepth  Fevap    Psi      Ksat     IMD     \n"
                    ";;-------------- -------- ---------- ----------- ---------- ---------------------------- --------- --------          -------- --------\n")
        return header
    
    def print(self):
        #As storage Node
        header = f" ".join(str(x) for x in [self.name, self.elevation, self.maxdepth, self.initdepth, self.shape, self.curve.name, self.surdepth, self.fevap, self.psi, self.ksat, self.IMD, '\n'])
        return header
    

@dataclass(kw_only=True)
class OUTFALLS(SWMMConfigObject):
    name : str
    elevation : float
    Type : str
    stagedata : str
    Gated : str
    RouteTo : str

    @staticmethod
    def header():
        header = ("[OUTFALLS]\n"
                    ";;Name           Elevation  Type       Stage Data       Gated    Route To   \n"     
                    ";;-------------- ---------- ---------- ---------------- -------- ----------------\n")
        return header

@dataclass(kw_only=True)
class Auslass(OUTFALLS):
    Type : str = field(default="FREE")
    stagedata : str = field(default="   ")
    Gated : str = field(default="NO")
    RouteTo : str = field(default="")
    
    def print(self):
        header = f"{self.name} {self.elevation} {self.Type} {self.stagedata} {self.Gated} {self.RouteTo}\n"
        return header

@dataclass(kw_only=True)
class SpeicherSchacht(STORAGE):
    initdepth : float = field(default=0)
    shape : str = field(default="TABULAR")
    surdepth : float = field(default=0)
    fevap : float = field(default=0)
    psi : float = field(default = 0.0)
    ksat : float = field(default = 0.0)
    IMD : float = field(default = 0.0)


    
@dataclass(kw_only=True)
class Schacht(STORAGE):
    initdepth : float = field(default=0)
    shape : str = field(default="TABULAR")
    surdepth : float = field(default=0)
    fevap : float = field(default=0)
    psi : float = field(default = 0.0)
    ksat : float = field(default = 0.0)
    IMD : float = field(default = 0.0)

    


@dataclass(kw_only=True)
class CONDUITS(SWMMConfigObject):
    name : str
    fromnode : str
    tonode : str
    length : float
    roughness : float
    InOffset : float
    OutOffset : float
    InitFlow : float
    MaxFlow : float

    @staticmethod
    def header():
        header = ("[CONDUITS]\n"
                    ";;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow \n"  
                    ";;-------------- ---------------- ---------------- ---------- ---------- ---------- ---------- ---------- ----------\n"
                    )
        return header
    
    def print(self):
        header = f" ".join(str(x) for x in [self.name, self.fromnode, self.tonode, self.length, self.roughness, self.InOffset, self.OutOffset, self.InitFlow, self.MaxFlow, '\n'])
        return header


@dataclass(kw_only=True)
class PUMPS(SWMMConfigObject):
    name : str
    fromnode : str
    tonode : str
    curve : Curve
    status : str
    startup : str
    shutoff : str

    @staticmethod
    def header():
        pump_header = ("[PUMPS]\n"
                        ";;Name           From Node        To Node          Pump Curve       Status   Sartup Shutoff \n"
                        ";;-------------- ---------------- ---------------- ---------------- ------ -------- --------\n"
                        )
        return pump_header
    def print(self):
        pump_header = f"{self.name}         {self.fromnode}               {self.tonode}               {self.curve.name}         {self.status}      {self.startup}        {self.shutoff}      \n"
        return pump_header

@dataclass(kw_only=True)
class PumpHextran(PUMPS):
    """Simplified model"""
    status : str = field(default = "OFF")
    startup : str = field(default = "0")
    shutoff : str = field(default = "0")

@dataclass(kw_only=True)
class CONTROLS(SWMMConfigObject):
    
    @staticmethod
    def header():
        rules_header = "[CONTROLS]\n"
        return rules_header

@dataclass(kw_only=True)
class RULES(CONTROLS):
    multiline_text : str

    def print(self):
        return self.multiline_text

@dataclass(kw_only=True)
class WEIRS(SWMMConfigObject):
    name : str
    fromnode : str
    tonode : str
    Type : str
    CrestHt : float
    Qcoeff : float
    Gated : str
    EndCon  : float
    EndCoeff : float
    Surcharge : str
    RoadWidth : float
    RoadSurf : float
    CoeffCurve : float

    @staticmethod
    def header():
        header = ("[WEIRS]\n"
                    ";;Name           From Node        To Node          Type         CrestHt    Qcoeff     Gated    EndCon   EndCoeff   Surcharge  RoadWidth  RoadSurf   Coeff. Curve\n"
                    ";;-------------- ---------------- ---------------- ------------ ---------- ---------- -------- -------- ---------- ---------- ---------- ---------- ----------------\n")
                    # 1                FLS062           FLS061           TRANSVERSE   0          3.33       NO       0        0          YES       
                    # 3                F2               FLR064           TRANSVERSE   0          3.33       NO       0        0          YES       
        return header
    

    def print(self):
        header = f"{self.name} {self.fromnode} {self.tonode} {self.Type} {self.CrestHt} {self.Qcoeff} {self.Gated} {self.EndCon} {self.EndCoeff} {self.Surcharge} {self.RoadWidth} {self.RoadSurf} {self.CoeffCurve}\n"
        return header
    
                

@dataclass(kw_only=True)
class WeirHextran(WEIRS):
    # Type : str #From Getprofil
    Gated : str = field(default="NO")
    EndCon  : float = field(default=0)
    EndCoeff : float = field(default=0)
    Surcharge : str = field(default="YES")
    RoadWidth : float = field(default=0.0)
    RoadSurf : float = field(default=0.0)
    CoeffCurve : float = field(default=0.0)

    @staticmethod
    def get_profiltyp(typ : int):
            if typ == 52: return "TRANSVERSE"
            else:
                print(f"Unknown type of weir {typ}. Fallback TRANSVERSE")
                return "TRANSVERSE"
            

@dataclass(kw_only=True)
class XSECTIONS(SWMMConfigObject):
        name : str
        shape : str #CUSTOM for custom
        geom1 : float
        geom2 : float
        geom3 : float
        geom4 : float
        barrels : float = field(default=0)
        culvert : float = field(default=0)
        

        @staticmethod
        def header():
            #Geom1 Height, Geom2 Laenge, SHAPE RECT_OPEN, Link Name of the Weir
            xsection = ("[XSECTIONS]\n"
                        ";;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    Culvert \n"  
                        ";;-------------- ------------ ---------------- ---------- ---------- ---------- ---------- ----------\n"
                        )
            return xsection
        
        def print(self):
            xsection = f"{self.name}  {self.shape}    {self.geom1}  {self.geom2} {self.geom3} {self.geom4} {self.barrels}   {self.culvert}         \n"
            return xsection        

        @staticmethod
        def get_shape(profiltyp : str)->str:
            """Converts the Profiltyp from hystem extran to swmm """
            if profiltyp == "1": return "CIRCULAR"
            if profiltyp == "2": return "RECT_CLOSED"
            if profiltyp == "3": return "EGG"
            if profiltyp == "68": return "CUSTOM"
            else:
                logging.error(f"Profiltyp {profiltyp} not implemented yet! Created as circular!!")
                return "CIRCULAR"
        


@dataclass(kw_only=True)
class COORDINATES(SWMMConfigObject):
    name : str
    x : list[float]
    y : list[float]

    def __post_init__(self): #Notsure if this really needed but here we go
        if not isinstance(self.x, list): self.x = [self.x]
        if not isinstance(self.y, list): self.y = [self.y]


    @staticmethod
    def header():
        """COORDINATES FOR NODES"""
        header = ("[COORDINATES]\n"
                    ";;Node           X-Coord            Y-Coord\n"           
                    ";;-------------- ------------------ ------------------\n")
        return header
    
    def print(self):
        line = ""
        for x, y in zip(self.x, self.y):
            line += f"{self.name} {x} {y}\n"
        return line

@dataclass(kw_only=True)
class SUBAREAS(SWMMConfigObject):
    subcatchment_name : str
    RouteTo : str = field(default="OUTLET" ) #Subarea routing
    N_imperv : float = field(default=0.01)   
    N_perv : float = field(default=0.1) 
    S_imperv : float = field(default=0.05) 
    S_perv : float = field(default=0.05 ) 
    PctZero : float = field(default=25) #Pct Routed to Pervious area and available for infiltration
    PctRouted : float = field(default=0.0) 

    @staticmethod
    def header():
        header = ("[SUBAREAS]\n"
                    ";;Subcatchment   N-Imperv   N-Perv     S-Imperv   S-Perv     PctZero    RouteTo    PctRouted \n"         
                    ";;-------------- ---------- ---------- ---------- ---------- ---------- ---------- ----------\n"
                    )
        return header


    def print(self):
        line = " ".join(str(x) for x in [self.subcatchment_name, self.N_imperv, self.N_perv, self.S_imperv, self. S_perv, self.PctZero, self.RouteTo, self.PctRouted, "\n"])
        return line


@dataclass(kw_only=True)
class RAINGAGES(SWMMConfigObject):
    name : str
    format : str
    interval : str
    SCF : str
    Source : str

    @staticmethod
    def header():
        header = ("[RAINGAGES]\n"
                    ";;Name           Format    Interval SCF      Source    \n"
                    ";;-------------- --------- ------ ------ ----------\n")
        return header
    
    def print(self):
        line = " ".join(str(x) for x in [self.name, self.format, self.interval, self.SCF, self.Source, "\n"])
        return line


@dataclass(kw_only=True)
class SUBCATCHMENTS(SWMMConfigObject):    
    name : str
    raingage_name : str = field(default="*") 
    outlet : str = field(default="*") 
    area : float
    pct_imperv : float = field(default=25) 
    width : float #Normally its the area / longest distance to outlet
    pct_slope : float
    curblen : float = field(default = 0) 
    snowpack : float = field(default = 0.0) 

    @staticmethod
    def header():
        header = ("[SUBCATCHMENTS]\n"
                    ";;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope   CurbLen  SnowPack   \n"     
                    ";;-------------- ---------------- ---------------- -------- -------- -------- -------- -------- ----------------\n"
        )
        return header
    
    def print(self):
        return " ".join(str(x) for x in [self.name, self.raingage_name, self.outlet, self.area, self.pct_imperv,self.width,self.pct_slope,self.curblen, self.snowpack,"\n"])
  
@dataclass(kw_only=True)
class INFILTRATION(SWMMConfigObject):    
    subcatchment_name : str
    param1 : float = field(default=3)
    param2 : float = field(default=0.5)
    param3 : float = field(default=4)
    param4 : float = field(default=7)
    param5 : float = field(default=0)

    @staticmethod
    def header():
        header = ("[INFILTRATION]\n"
                    ";;Subcatchment   Param1     Param2     Param3     Param4     Param5    \n"
                    ";;-------------- ---------- ---------- ---------- ---------- ----------\n"
                )
        return header
    

    def print(self):
        return " ".join(str(x) for x in [self.subcatchment_name, self. param2, self. param2, self. param3, self. param4, self. param5,"\n"])

    

@dataclass(kw_only=True)
class Polygons(SWMMConfigObject):
    subcatchment_name : str
    x : list[float]
    y : list[float]


    def __post_init__(self): #Notsure if this really needed but here we go
        if not isinstance(self.x, list): self.x = [self.x]
        if not isinstance(self.y, list): self.y = [self.y]


    @staticmethod
    def header():
        header = ("[Polygons]\n"
                    ";;Subcatchment   X-Coord            Y-Coord  \n"         
                    ";;-------------- ------------------ ------------------\n")
        return header


    def print(self):
        line = ""
        for x, y in zip(self.x, self.y):
            line += " ".join(str(x) for x in [self.subcatchment_name, x, y, "\n"])
        return line


