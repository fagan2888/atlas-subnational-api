from colombia import models, create_app
from colombia.core import db

from dataset_tools import (process_dataset, classification_to_models)

import pandas as pd
import numpy as np


def weighted_mean(data_field, weights_field):
    """Return a function that, when applied to a dataframe groupby, returns a
    weighted mean."""

    def inner(groupby):
        d = groupby[data_field]
        w = groupby[weights_field]
        w_sum = w.sum()
        if w_sum == 0 or pd.isnull(w_sum):
            return np.nan
        return (d * w).sum() / w.sum()

    return inner


if __name__ == "__main__":

        app = create_app()
        with app.app_context():

            c = app.config

            from datasets import (
                trade4digit_country, trade4digit_department,
                trade4digit_msa, trade4digit_municipality,
                industry4digit_country, industry4digit_department,
                industry4digit_msa, industry2digit_department,
                industry4digit_municipality,
                trade4digit_rcpy_municipality,
                industry2digit_msa,
                trade4digit_rcpy_department, trade4digit_rcpy_msa,
                trade4digit_rcpy_country, population,
                gdp_nominal_department, gdp_real_department,
                occupation2digit, occupation2digit_industry2digit,
                industry2digit_country, livestock_level1_country,
                livestock_level1_department,
                livestock_level1_municipality,
                agproduct_level3_country, agproduct_level3_department,
                agproduct_level3_municipality,
                nonagric_level3_country, nonagric_level3_department,
                nonagric_level3_municipality,
                land_use_level2_country, land_use_level2_department,
                land_use_level2_municipality, farmtype_level2_country,
                farmtype_level2_department, farmtype_level2_municipality,
                farmsize_level1_country, farmsize_level1_department,
                farmsize_level1_municipality,
            )

            from datasets import (
                product_classification,
                industry_classification,
                location_classification,
                country_classification,
                occupation_classification,
                livestock_classification,
                agproduct_classification,
                nonagric_classification,
                land_use_classification,
                farmtype_classification,
                farmsize_classification,
            )


            products = classification_to_models(product_classification,
                                                models.HSProduct)
            db.session.add_all(products)
            db.session.commit()

            locations = classification_to_models(location_classification,
                                                 models.Location)
            db.session.add_all(locations)
            db.session.commit()

            industries = classification_to_models(industry_classification,
                                                  models.Industry)
            db.session.add_all(industries)
            db.session.commit()

            occupations = classification_to_models(occupation_classification,
                                                  models.Occupation)
            db.session.add_all(occupations)
            db.session.commit()

            livestock = classification_to_models(livestock_classification,
                                                  models.Livestock)
            db.session.add_all(livestock)
            db.session.commit()

            agproduct = classification_to_models(agproduct_classification,
                                                  models.AgriculturalProduct)
            db.session.add_all(agproduct)
            db.session.commit()

            nonagric = classification_to_models(nonagric_classification,
                                                  models.NonagriculturalActivity)
            db.session.add_all(nonagric)
            db.session.commit()

            land_use = classification_to_models(land_use_classification,
                                                  models.LandUse)
            db.session.add_all(land_use)
            db.session.commit()

            farmtype = classification_to_models(farmtype_classification,
                                                  models.FarmType)
            db.session.add_all(farmtype)
            db.session.commit()

            farmsize = classification_to_models(farmsize_classification,
                                                  models.FarmSize)
            db.session.add_all(farmsize)
            db.session.commit()

            countries = classification_to_models(country_classification,
                                                  models.Country)
            db.session.add_all(countries)
            db.session.commit()

            # Country product year
            ret = process_dataset(trade4digit_country)

            df = ret[('location_id', 'product_id', 'year')].reset_index()
            df["level"] = "4digit"
            df.to_sql("country_product_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Department product year
            ret = process_dataset(trade4digit_department)

            df = ret[('product_id', 'year')].reset_index()
            df["level"] = "4digit"
            df.to_sql("product_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            df = ret[('location_id', 'product_id', 'year')].reset_index()
            df["level"] = "4digit"
            df.to_sql("department_product_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Department-year product
            dy_p = ret[('location_id', 'year')].reset_index()

            # Department - year industry
            ret = process_dataset(industry4digit_department)
            dy_i = ret[('location_id', 'year')].reset_index()

            # GDP data
            ret = process_dataset(gdp_real_department)
            gdp_real_df = ret[('location_id', 'year')]

            ret = process_dataset(gdp_nominal_department)
            gdp_nominal_df = ret[('location_id', 'year')]

            gdp_df = gdp_real_df.join(gdp_nominal_df).reset_index()

            # Pop data
            ret = process_dataset(population)
            pop_df = ret[('location_id', 'year')].reset_index()

            ret = process_dataset(livestock_level1_department)
            ls_df = ret[('location_id',)].reset_index()
            ls_df["average_livestock_load"] = ls_df.num_livestock / ls_df.num_farms
            ls_df["year"] = c["YEAR_AGRICULTURAL_CENSUS"]
            ls_df = ls_df[["location_id", "average_livestock_load", "year"]]

            # Yield indexes
            ret = process_dataset(agproduct_level3_department)
            agproduct_df = ret[('location_id', 'agproduct_id', 'year')].reset_index()
            agproduct_df = agproduct_df\
                .groupby(["location_id", "year"])\
                .apply(weighted_mean("yield_index", "land_harvested"))
            agproduct_df.name = "yield_index"
            agproduct_df = agproduct_df.reset_index()

            # Merge all dept-year variables together
            def filter_year_range(df, min_year, max_year):
                return df[(min_year <= df.year) & (df.year <= max_year)]

            df_p = filter_year_range(dy_p, c["YEAR_MIN_TRADE"], c["YEAR_MAX_TRADE"])
            df_i = filter_year_range(dy_i, c["YEAR_MIN_INDUSTRY"], c["YEAR_MAX_INDUSTRY"])
            gdp_df = filter_year_range(gdp_df, c["YEAR_MIN_DEMOGRAPHIC"], c["YEAR_MAX_DEMOGRAPHIC"])
            pop_df = filter_year_range(pop_df, c["YEAR_MIN_DEMOGRAPHIC"], c["YEAR_MAX_DEMOGRAPHIC"])
            ls_df = filter_year_range(ls_df, c["YEAR_AGRICULTURAL_CENSUS"], c["YEAR_AGRICULTURAL_CENSUS"])
            agproduct_df = filter_year_range(agproduct_df, c["YEAR_MIN_AGPRODUCT"], c["YEAR_MAX_AGPRODUCT"])

            dy = dy_p.merge(dy_i, on=["location_id", "year"], how="outer")
            dy = dy.merge(gdp_df, on=["location_id", "year"], how="outer")
            dy = dy.merge(pop_df, on=["location_id", "year"], how="outer")
            dy = dy.merge(ls_df, on=["location_id", "year"], how="left")
            dy = dy.merge(agproduct_df, on=["location_id", "year"], how="left")

            dy["gdp_pc_nominal"] = dy.gdp_nominal / dy.population
            dy["gdp_pc_real"] = dy.gdp_real / dy.population

            dy.to_sql("department_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Municipality product year
            ret = process_dataset(trade4digit_municipality)

            df = ret[('location_id', 'product_id', 'year')].reset_index()
            df["level"] = "4digit"
            df.to_sql("municipality_product_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # MSA product year
            ret = process_dataset(trade4digit_msa)

            df = ret[('location_id', 'product_id', 'year')].reset_index()
            df["level"] = "4digit"
            df.to_sql("msa_product_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            trade_msa_year = ret[('location_id', 'year')]

            # Country - trade rcpy
            ret = process_dataset(trade4digit_rcpy_country)

            df = ret[("country_id", "location_id", "year")].reset_index()
            df.to_sql("country_country_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            df = ret[("product_id", "country_id", "year")].reset_index()
            df["level"] = "4digit"
            df.to_sql("partner_product_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            # MSA - trade rcpy
            ret = process_dataset(trade4digit_rcpy_msa)

            df = ret[("country_id", "location_id", "year")].reset_index()
            df.to_sql("country_msa_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            # Municipality - trade rcpy
            ret = process_dataset(trade4digit_rcpy_municipality)

            df = ret[("country_id", "location_id", "year")].reset_index()
            df.to_sql("country_municipality_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            df = ret[("country_id", "location_id", "product_id", "year")].reset_index()
            df["level"] = "4digit"
            df.to_sql("country_municipality_product_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            # Department - trade rcpy
            ret = process_dataset(trade4digit_rcpy_department)

            df = ret[("country_id", "location_id", "product_id", "year")].reset_index()
            df["level"] = "4digit"
            df.to_sql("country_department_product_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            df = ret[("country_id", "location_id", "year")].reset_index()
            df.to_sql("country_department_year", db.engine,
                      index=False, chunksize=10000, if_exists="append")

            # Country - industry- y ear
            ret = process_dataset(industry4digit_country)
            df = ret[('location_id', 'industry_id', 'year')].reset_index()
            df["level"] = "class"
            df.to_sql("country_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Department - industry - year
            ret = process_dataset(industry4digit_department)

            df = ret[('industry_id', 'year')].reset_index()
            df["level"] = "class"
            df.to_sql("industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            df = ret[('location_id', 'industry_id', 'year')].reset_index()
            df["level"] = "class"
            df.to_sql("department_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Country - two digit industry - year
            ret = process_dataset(industry2digit_country)
            df = ret[('industry_id', 'year')].reset_index()
            df["level"] = "division"
            df.to_sql("industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Department - two digit industry - year
            ret = process_dataset(industry2digit_department)

            df = ret[('location_id', 'industry_id', 'year')].reset_index()
            df["level"] = "division"
            df.to_sql("department_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # MSA - two digit industry - year
            ret = process_dataset(industry2digit_msa)

            df = ret[('location_id', 'industry_id', 'year')].reset_index()
            df["level"] = "division"
            df.to_sql("msa_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # MSA - industry - year
            ret = process_dataset(industry4digit_msa)

            df = ret[('location_id', 'industry_id', 'year')].reset_index()
            df["level"] = "class"
            df.to_sql("msa_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            industry_msa_year = ret[('location_id', 'year')]

            # MSA year
            msa_year = industry_msa_year.join(trade_msa_year).reset_index()
            msa_year.to_sql("msa_year", db.engine, index=False,
                            chunksize=10000, if_exists="append")


            # Municipality - industry - year
            ret = process_dataset(industry4digit_municipality)
            df = ret[('location_id', 'industry_id', 'year')].reset_index()
            df["level"] = "class"
            df.to_sql("municipality_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Livestock - country
            ret = process_dataset(livestock_level1_country)
            df = ret[('location_id', 'livestock_id')].reset_index()
            df["livestock_level"] = "level1"
            df.to_sql("country_livestock_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Livestock - department
            ret = process_dataset(livestock_level1_department)
            df = ret[('location_id', 'livestock_id')].reset_index()
            df["livestock_level"] = "level1"
            df.to_sql("department_livestock_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            df = ret[('location_id',)].reset_index()
            df["average_livestock_load"] = df.num_livestock / df.num_farms
            df = df.drop(["num_livestock", "num_farms"], axis=1)
            df["livestock_level"] = "level1"
            df.to_sql("livestock_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Livestock - municipality
            ret = process_dataset(livestock_level1_municipality)
            df = ret[('location_id', 'livestock_id')].reset_index()
            df["livestock_level"] = "level1"
            df.to_sql("municipality_livestock_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            ls_df = ret[('location_id',)].reset_index()
            ls_df["average_livestock_load"] = ls_df.num_livestock / ls_df.num_farms
            ls_df["year"] = c["YEAR_AGRICULTURAL_CENSUS"]
            ls_df = ls_df[["location_id", "average_livestock_load", "year"]]

            ret = process_dataset(agproduct_level3_municipality)
            agproduct_df = ret[('location_id', 'agproduct_id', 'year')].reset_index()
            agproduct_df = agproduct_df\
                .groupby(["location_id", "year"])\
                .apply(weighted_mean("yield_index", "land_harvested"))
            agproduct_df.name = "yield_index"
            agproduct_df = agproduct_df.reset_index()

            my = ls_df.merge(agproduct_df, on=["location_id", "year"], how="outer")
            my.to_sql("municipality_year", db.engine, index=False,
                         chunksize=10000, if_exists="append")

            # AgriculturalProduct - country
            ret = process_dataset(agproduct_level3_country)
            df = ret[('location_id', 'agproduct_id', 'year')].reset_index()
            df["agproduct_level"] = "level3"
            df.to_sql("country_agproduct_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # AgriculturalProduct - department
            ret = process_dataset(agproduct_level3_department)
            df = ret[('location_id', 'agproduct_id', 'year')].reset_index()
            df["agproduct_level"] = "level3"
            df.to_sql("department_agproduct_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # AgriculturalProduct - municipality
            ret = process_dataset(agproduct_level3_municipality)
            df = ret[('location_id', 'agproduct_id', 'year')].reset_index()
            df["agproduct_level"] = "level3"
            df.to_sql("municipality_agproduct_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Nonagric - country
            ret = process_dataset(nonagric_level3_country)
            df = ret[('location_id', 'nonag_id')].reset_index()
            df["nonag_level"] = "level3"
            df.to_sql("country_nonag_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Nonagric - department
            ret = process_dataset(nonagric_level3_department)
            df = ret[('location_id', 'nonag_id')].reset_index()
            df["nonag_level"] = "level3"
            df.to_sql("department_nonag_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Nonagric - municipality
            ret = process_dataset(nonagric_level3_municipality)
            df = ret[('location_id', 'nonag_id')].reset_index()
            df["nonag_level"] = "level3"
            df.to_sql("municipality_nonag_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")


            # LandUse - country
            ret = process_dataset(land_use_level2_country)
            df = ret[('location_id', 'land_use_id')].reset_index()
            df["land_use_level"] = "level2"
            df.to_sql("country_land_use_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # LandUse - department
            ret = process_dataset(land_use_level2_department)
            df = ret[('location_id', 'land_use_id')].reset_index()
            df["land_use_level"] = "level2"
            df.to_sql("department_land_use_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # LandUse - municipality
            ret = process_dataset(land_use_level2_municipality)
            df = ret[('location_id', 'land_use_id')].reset_index()
            df["land_use_level"] = "level2"
            df.to_sql("municipality_land_use_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # FarmType - country
            ret = process_dataset(farmtype_level2_country)
            df = ret[('location_id', 'farmtype_id')].reset_index()
            df["farmtype_level"] = "level2"
            df.to_sql("country_farmtype_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # FarmType - department
            ret = process_dataset(farmtype_level2_department)
            df = ret[('location_id', 'farmtype_id')].reset_index()
            df["farmtype_level"] = "level2"
            df.to_sql("department_farmtype_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # FarmType - municipality
            ret = process_dataset(farmtype_level2_municipality)
            df = ret[('location_id', 'farmtype_id')].reset_index()
            df["farmtype_level"] = "level2"
            df.to_sql("municipality_farmtype_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # FarmSize - country
            ret = process_dataset(farmsize_level1_country)
            df = ret[('location_id', 'farmsize_id')].reset_index()
            df["farmsize_level"] = "level1"
            df.to_sql("country_farmsize_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # FarmSize - department
            ret = process_dataset(farmsize_level1_department)
            df = ret[('location_id', 'farmsize_id')].reset_index()
            df["farmsize_level"] = "level1"
            df.to_sql("department_farmsize_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # FarmSize - municipality
            ret = process_dataset(farmsize_level1_municipality)
            df = ret[('location_id', 'farmsize_id')].reset_index()
            df["farmsize_level"] = "level1"
            df.to_sql("municipality_farmsize_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Occupation - year
            ret = process_dataset(occupation2digit)
            df = ret[('occupation_id')].reset_index()
            df["level"] = "minor_group"
            df.to_sql("occupation_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

            # Occupation - industry - year
            ret = process_dataset(occupation2digit_industry2digit)
            df = ret[('occupation_id', 'industry_id')].reset_index()
            df["level"] = "minor_group"
            df.to_sql("occupation_industry_year", db.engine, index=False,
                      chunksize=10000, if_exists="append")

