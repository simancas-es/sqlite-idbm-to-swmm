

import pandas
from functools import partial

from sqlite_to_swmm import SQLitetoSWMM, assign_regenschreiber, sqlite_dump
import logging
LOG_PATH = "output_errors.log"
handlers = [logging.StreamHandler()]
if LOG_PATH:
        handlers.append(logging.FileHandler(LOG_PATH))
logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )

def manual_convert():
    """
    Edit this by hand
    """
    path = r"example.idbm"
    swmm_path = r"example.inp"

    converter = SQLitetoSWMM(sqlite_path=path, swmm_path=swmm_path, spatialite_dll_path = "mod_spatialite.dll")

    pandasRS = None
    #Regenschreiber assignment
    pandasRS = pandas.read_csv(r"example_scid-rsid.csv")
    assert pandasRS["SCID"].is_unique

    objects = converter.object_extraction(individual_regenschreiber = partial(assign_regenschreiber, df = pandasRS))
    path = converter.convert(write = True, object_collection = objects)
    
if __name__ == "__main__":
    manual_convert()

    pass