"""Tools for creating and manipulating neighborhood datasets."""

import multiprocessing
import os
import pathlib
from warnings import warn

from appdirs import user_data_dir

import geopandas as gpd
import pandas as pd
import quilt3
from requests.exceptions import Timeout
from shapely import wkb, wkt

appname = "geosnap"
appauthor = "geosnap"
data_dir = user_data_dir(appname, appauthor)
if not os.path.exists(data_dir):
    pathlib.Path(data_dir).mkdir(parents=True, exist_ok=True)

# look for local storage and create if missing
try:
    from quilt3.data.geosnap_data import storage
except ImportError:
    storage = quilt3.Package()


class _Map(dict):
    """
    tabbable dict.
    """

    def __init__(self, *args, **kwargs):
        super(_Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.iteritems():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.iteritems():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(_Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(_Map, self).__delitem__(key)
        del self.__dict__[key]


def _deserialize_wkb(str):
    return wkb.loads(str, hex=True)


def _deserialize_wkt(str):
    return wkt.loads(str)


def _convert_gdf(df):
    """Convert DataFrame to GeoDataFrame.

    DataFrame to GeoDataFrame by converting wkt/wkb geometry representation
    back to Shapely object.

    Parameters
    ----------
    df : pandas.DataFrame
        dataframe with column named either "wkt" or "wkb" that stores
        geometric information as well-known text or well-known binary,
        (hex encoded) respectively.

    Returns
    -------
    gpd.GeoDataFrame
        geodataframe with converted `geometry` column.

    """
    df = df.copy()
    df.reset_index(inplace=True, drop=True)

    if "wkt" in df.columns.tolist():
        with multiprocessing.Pool() as P:
            df["geometry"] = P.map(_deserialize_wkt, df["wkt"])
        df = df.drop(columns=["wkt"])

    else:
        with multiprocessing.Pool() as P:
            df["geometry"] = P.map(_deserialize_wkb, df["wkb"])
        df = df.drop(columns=["wkb"])

    df = gpd.GeoDataFrame(df)
    df.crs = {"init": "epsg:4326"}

    return df


class DataStore(object):
    """Storage for geosnap data. Currently supports US Census data."""

    def __init__(self):
        """Instantiate a new DataStore object."""
        try:  # if any of these aren't found, stream them insteead
            from quilt3.data.census import tracts_cartographic, administrative
        except ImportError:
            warn(
                "Unable to locate local census data. Streaming instead.\n"
                "If you plan to use census data repeatedly you can store it locally "
                "with the data.store_census function for better performance"
            )
            try:
                tracts_cartographic = quilt3.Package.browse(
                    "census/tracts_cartographic", "s3://quilt-cgs"
                )
                administrative = quilt3.Package.browse(
                    "census/administrative", "s3://quilt-cgs"
                )

            except Timeout:
                warn(
                    "Unable to locate local census data and unable to reach s3 bucket."
                    "You will be unable to use built-in data during this session. "
                    "If you need these data, please try downloading a local copy "
                    "with the data.store_census function, then restart your "
                    "python kernel and try again."
                )
        self.tracts_cartographic = tracts_cartographic
        self.administrative = administrative

    def __dir__(self):

        atts = [
            "blocks_2000",
            "blocks_2010",
            "codebook",
            "counties",
            "ltdb",
            "msa_definitions",
            "msas",
            "ncdb",
            "states",
            "tracts_1990",
            "tracts_2000",
            "tracts_2010",
        ]

        return atts

    def blocks_2000(self, states=None, convert=True, fips=None):
        """Census blocks for 2000.

        Parameters
        ----------
        states : list-like
            list of state fips codes to return as a datafrrame.
        convert : bool
        if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        type
        pandas.DataFrame or geopandas.GeoDataFrame.
            2000 blocks as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        try:  # if any of these aren't found, stream them insteead
            from quilt3.data.census import blocks_2000
        except ImportError:
            warn(
                "Unable to locate local census 2000 block data. Streaming instead.\n"
                "If you plan to use census data repeatedly you can store it locally "
                "with the data.store_blocks_2000 function for better performance"
            )
            try:
                blocks_2000 = quilt3.Package.browse(
                    "census/blocks_2000", "s3://quilt-cgs"
                )

            except Timeout:
                warn(
                    "Unable to locate local census data and unable to reach s3 bucket."
                    "You will be unable to use built-in data during this session. "
                    "Try downloading a local copy with the data.store_blocks_2000 function,"
                    "then restart your python kernel and try again."
                )

        if isinstance(states, (str,)):
            states = [states]
        if isinstance(states, (int,)):
            states = [states]
        blks = {}
        for state in states:
            blks[state] = blocks_2000[f"{state}.parquet"]()
            if fips:
                print(fips)
                blks[state] = blks[state][blks[state]["geoid"].str.startswith(fips)]
            blks[state]["year"] = 2000
        blocks = list(blks.values())
        blocks = pd.concat(blocks, sort=True)
        if convert:
            return _convert_gdf(blocks)
        return blocks

    def blocks_2010(self, states=None, convert=True, fips=None):
        """Census blocks for 2010.

        Parameters
        ----------
        states : list-like
            list of state fips codes to return as a datafrrame.
        convert : bool
        if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        type
        pandas.DataFrame or geopandas.GeoDataFrame.
            2010 blocks as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        try:  # if any of these aren't found, stream them insteead
            from quilt3.data.census import blocks_2010
        except ImportError:
            warn(
                "Unable to locate local census 2010 block data. Streaming instead.\n"
                "If you plan to use census data repeatedly you can store it locally "
                "with the data.store_blocks_2010 function for better performance"
            )
            try:
                blocks_2010 = quilt3.Package.browse(
                    "census/blocks_2010", "s3://quilt-cgs"
                )

            except Timeout:
                warn(
                    "Unable to locate local census data and unable to reach s3 bucket."
                    "You will be unable to use built-in data during this session. "
                    "If you need these data, please try downloading a local copy "
                    "with the data.store_blocks_2010 function, then restart your "
                    "python kernel and try again."
                )

        if isinstance(states, (str, int)):
            states = [states]
        blks = {}
        for state in states:
            blks[state] = blocks_2010[f"{state}.parquet"]()
            if fips:
                blks[state] = blks[state][blks[state]["geoid"].str.startswith(fips)]

            blks[state]["year"] = 2010
        blocks = list(blks.values())
        blocks = pd.concat(blocks, sort=True)
        if convert:
            return _convert_gdf(blocks)
        return blocks

    def tracts_1990(self, states=None, convert=True):
        """Nationwide Census Tracts as drawn in 1990 (cartographic 500k).

        Parameters
        ----------
        states : list-like
            list of state fips to subset the national dataframe
        convert : bool
            if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        pandas.DataFrame or geopandas.GeoDataFrame.
            1990 tracts as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        t = self.tracts_cartographic["tracts_1990_500k.parquet"]()
        if states:
            t = t[t.geoid.str[:2].isin(states)]
        t["year"] = 1990
        if convert:
            return _convert_gdf(t)
        else:
            return t

    def tracts_2000(self, states=None, convert=True):
        """Nationwide Census Tracts as drawn in 2000 (cartographic 500k).

        Parameters
        ----------
        states : list-like
            list of state fips to subset the national dataframe
        convert : bool
            if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        pandas.DataFrame.
            2000 tracts as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        t = self.tracts_cartographic["tracts_2000_500k.parquet"]()
        if states:
            t = t[t.geoid.str[:2].isin(states)]
        t["year"] = 2000
        if convert:
            return _convert_gdf(t)
        else:
            return t

    def tracts_2010(self, states=None, convert=True):
        """Nationwide Census Tracts as drawn in 2010 (cartographic 500k).

        Parameters
        ----------
        states : list-like
            list of state fips to subset the national dataframe
        convert : bool
            if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        pandas.DataFrame.
            2010 tracts as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        t = self.tracts_cartographic["tracts_2010_500k.parquet"]()
        if states:
            t = t[t.geoid.str[:2].isin(states)]
        t["year"] = 2010
        if convert:
            return _convert_gdf(t)
        else:
            return t

    def msas(self, convert=True):
        """Metropolitan Statistical Areas as drawn in 2010.

        Parameters
        ----------
        convert : bool
            if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        geopandas.GeoDataFrame.
            2010 MSAs as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        if convert:
            return _convert_gdf(
                self.administrative["msas.parquet"]().sort_values(by="name")
            )
        return self.administrative["msas.parquet"]().sort_values(by="name")

    def states(self, convert=True):
        """States.

        Parameters
        ----------
        convert : bool
            if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        geopandas.GeoDataFrame.
            US States as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        if convert:
            return _convert_gdf(self.administrative["states.parquet"]())
        return self.administrative["states.parquet"]()

    def counties(self):
        """Nationwide counties as drawn in 2010.

        Parameters
        ----------
        convert : bool
            if True, return geodataframe, else return dataframe (the default is True).

        Returns
        -------
        geopandas.GeoDataFrame.
            2010 counties as a geodataframe or as a dataframe with geometry
            stored as well-known binary on the 'wkb' column.

        """
        return _convert_gdf(self.administrative["counties.parquet"]())

    @property
    def msa_definitions(self):
        """2010 Metropolitan Statistical Area definitions.

        Returns
        -------
        pandas.DataFrame.
            dataframe that stores state/county --> MSA crosswalk definitions.

        """
        return self.administrative["msa_definitions.parquet"]()

    @property
    def ltdb(self):
        """Longitudinal Tract Database (LTDB).

        Returns
        -------
        pandas.DataFrame or geopandas.GeoDataFrame
            LTDB as a long-form geo/dataframe

        """
        try:
            return storage["ltdb"]()
        except KeyError:
            print(
                "Unable to locate LTDB data. Try saving the data again "
                "using the `store_ltdb` function"
            )

    @property
    def ncdb(self):
        """Geolytics Neighborhood Change Database (NCDB).

        Returns
        -------
        pandas.DataFrarme
            NCDB as a long-form dataframe

        """
        try:
            return storage["ncdb"]()
        except KeyError:
            print(
                "Unable to locate NCDB data. Try saving the data again "
                "using the `store_ncdb` function"
            )

    @property
    def codebook(self):
        """Codebook.

        Returns
        -------
        pandas.DataFrame.
            codebook that stores variable names, definitions, and formulas.

        """
        return pd.read_csv(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "io/variables.csv")
        )


datasets = DataStore()
