"""Fetch historical covid-19 data from multpile sources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# system packages
import urllib
import json
import datetime
import io

# additional packages
import pandas

class DataAcquisition:
  """An Utility class for data acquisition."""

  def fetch_infection_data_from_rki(bundesland:str="Hamburg",offset=0):
      """
      Fetch Covid-19-Cases from 
      https://experience.arcgis.com/experience/478220a4c454480e823b17327b2bf1d4/page/page_0/
      
      Args:
          bundesland: written like displayed on the website, a string
      Returns:
          a Dataframe containing all historical infections data of a bundesland
      """
      
      url_endpoint = "https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/RKI_COVID19/FeatureServer/0/query"
      params = {
          'f': 'json', 
          'where': f'Bundesland=\'{bundesland}\'',
          'returnGeometry': 'false',
          'spatialRel': 'esriSpatialRelIntersects',
          'outFields': 'ObjectId,AnzahlFall,Meldedatum,Geschlecht,Altersgruppe',
          'orderByFields': 'Meldedatum asc',
          'resultOffset': offset,
          'resultRecordCount': 2000,
          'cacheHint': "true"    
      }

      url_query = f"{url_endpoint}?{urllib.parse.urlencode(params)}"

      with urllib.request.urlopen(url_query) as url:
          data = json.loads(url.read().decode())['features']
      
      data_list = [
          (datetime.datetime.fromtimestamp(x['attributes']['Meldedatum'] / 1e3), x['attributes']['AnzahlFall'],x['attributes']['Geschlecht'],x['attributes']['Altersgruppe'],bundesland) 
          for x in data
      ]
      
      df = pandas.DataFrame(data_list, columns=['Meldedatum', 'Neuinfektionen', 'Geschlecht','Altersgruppe','Bundesland'])

      if len(data_list)>= 2000:
          df = df.append(fetch_infection_data_from_rki(bundesland,offset+2000))
      
      return df

  def fetch_death_data_from_rki(bundesland:str="Hamburg",offset=0):
      """
      Fetch Covid-19-Cases from 
      https://experience.arcgis.com/experience/478220a4c454480e823b17327b2bf1d4/page/page_0/
      
      Args:
          bundesland: written like displayed on the website, a string
      Returns:
          a Dataframe containing all historical infections data of a bundesland
      """
      
      url_endpoint = "https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/RKI_COVID19/FeatureServer/0/query"
      params = {
          'f': 'json', 
          'where': f'Bundesland=\'{bundesland}\' AND AnzahlTodesfall>0',
          'returnGeometry': 'false',
          'spatialRel': 'esriSpatialRelIntersects',
          'outFields': 'ObjectId,AnzahlTodesfall,Meldedatum,Geschlecht,Altersgruppe',
          'orderByFields': 'Meldedatum asc',
          'resultOffset': offset,
          'resultRecordCount': 2000,
          'cacheHint': "true"    
      }

      url_query = f"{url_endpoint}?{urllib.parse.urlencode(params)}"

      with urllib.request.urlopen(url_query) as url:
          data = json.loads(url.read().decode())['features']
      
      data_list = [
          (datetime.datetime.fromtimestamp(x['attributes']['Meldedatum'] / 1e3), x['attributes']['AnzahlTodesfall'],x['attributes']['Geschlecht'],x['attributes']['Altersgruppe'],bundesland) 
          for x in data
      ]
      
      df = pandas.DataFrame(data_list, columns=['Meldedatum', 'Todesfaelle', 'Geschlecht','Altersgruppe','Bundesland'])

      if len(data_list)>= 2000:
          df = df.append(fetch_death_data_from_rki(bundesland,offset+2000))
      
      return df


  flatten = lambda l: [item for sublist in l for item in sublist]

  def get_all_dates_sorted(all_death_data,all_infection_data):
      infections_dates = set(all_infection_data.Meldedatum.unique())
      death_dates =  set(all_death_data.Meldedatum.unique())
      all_dates = list(infections_dates.union(death_dates))
      all_dates.sort()
      return all_dates

  def get_pivoted_country_data(all_death_data,all_infection_data):
      dates = get_all_dates_sorted(all_death_data,all_infection_data)
      bundeslaender = ["Baden-Württemberg","Nordrhein-Westfalen","Bayern","Hessen","Berlin",
                  "Niedersachsen","Sachsen","Rheinland-Pfalz","Brandenburg","Hamburg","Schleswig-Holstein"
                  ,"Thüringen","Mecklenburg-Vorpommern","Bremen","Saarland","Sachsen-Anhalt"]

      grouped_infection_data = all_infection_data.groupby(["Meldedatum","Bundesland"])
      grouped_death_data = all_death_data.groupby(["Meldedatum","Bundesland"])
      
      data = []
      for date in dates:
          row = [date]
          for bland in bundeslaender:
              try:
                  i_value = grouped_infection_data.get_group((date,bland)).sum()
                  row= row +[i_value['Neuinfektionen']]
              except(KeyError):
                  row= row +[0]
              try:
                  i_value = grouped_death_data.get_group((date,bland)).sum()
                  row= row +[i_value['Todesfaelle']]
              except(KeyError):
                  row= row +[0]
          data = data + [row]
      
      columns = ["Datum"]
      columns = columns + flatten([[f"RKI:Infektionen:{bland}",f"RKI:Todesfaelle:{bland}"] for bland in bundeslaender])
      
      df = pandas.DataFrame(data,columns=columns)
      
      for bland in bundeslaender:
          df[f'RKI:Summe_Infektionen:{bland}']= df[f'RKI:Infektionen:{bland}'].cumsum()
          df[f'RKI:Summe_Todesfaelle:{bland}']= df[f'RKI:Todesfaelle:{bland}'].cumsum()
          # remove deaths from infections
          df[f'RKI:Summe_Infektionen:{bland}']= df.apply(lambda row: row[f'RKI:Summe_Infektionen:{bland}'] - row[f'RKI:Summe_Todesfaelle:{bland}'] , axis = 1)

      return df

  def fetch_rki_data_mergable (self) -> pandas.DataFrame:
    rki_infection_data = fetch_infection_data_from_rki()
    rki_death_data = fetch_death_data_from_rki()
    return get_pivoted_country_data(rki_death_data,rki_infection_data)

  def fetch_germany_morgenpost(self) -> pandas.DataFrame:
    """
    Fetch Covid-19-Cases for Germany from 
    https://interaktiv.morgenpost.de/corona-virus-karte-infektionen-deutschland-weltweit/
    
    Args:

    Returns:
        a Dataframe containing all historical data from a bundesland
        cols = ['date','confirmed','recovered', 'deaths']
    """
    # download current history csv file
    url_query = 'https://interaktiv.morgenpost.de/corona-virus-karte-infektionen-deutschland-weltweit/data/Coronavirus.history.v2.csv'
        
    with urllib.request.urlopen(url_query) as url:
        csv_string = url.read().decode()

    # read csv from string
    df = pandas.read_csv(io.StringIO(csv_string))

    return df

  def fetch_bundesland_morgenpost(self, bundesland:str="Hamburg") -> pandas.DataFrame:
    """
    Fetch Covid-19-Cases for a bundeland from 
    https://interaktiv.morgenpost.de/corona-virus-karte-infektionen-deutschland-weltweit/
    
    Args:
        bundesland: written like displayed on the website, a string
    Returns:
        a Dataframe containing all historical data from a bundesland
        cols = ['date','confirmed','recovered', 'deaths']
    """
    df = self.fetch_germany_morgenpost()

    # filter by bundesland
    df_bundesland = df[df['label']==bundesland]

    # drop unnecessary collumns
    df_bundesland = df_bundesland[['date','confirmed','recovered', 'deaths']]

    return df_bundesland

  def load_general_stats(self, path:str="bundeslaender.csv") -> pandas.DataFrame:
    """
    Extracts bundesland statistical data from a csv file
    
    Args:
        path: path to bundesland csv, a string
    Returns:
        a Dataframe containing all historical data from a bundesland
        cols = ['date','confirmed','recovered', 'deaths']
    """

    return pandas.read_csv(path)

  def fetch_all_data(self) -> pandas.DataFrame:
    """
    merges all data together into one big csv
    
    Args:

    Returns:
        a Dataframe containing all historical data from a bundesland
        cols = ['date','{bundesland}:{source}:{value}','{bundesland}:info:population']
        source = ['rki', 'morgenpost']
    """
    df_info = self.load_general_stats()
    print(df_info)

    # create dataframe layout
    df_all_collumns = ['date']
    for bundesland in df_info['Bundesland']:
      df_all_collumns.append(f'{bundesland}:morgenpost:confirmed')
      df_all_collumns.append(f'{bundesland}:morgenpost:recovered')
      df_all_collumns.append(f'{bundesland}:morgenpost:deaths')
      df_all_collumns.append(f'{bundesland}:rki:infections')
      df_all_collumns.append(f'{bundesland}:rki:deaths')
      df_all_collumns.append(f'{bundesland}:info:population')
      
    df_all = pandas.DataFrame(columns=df_all_collumns)

    start_date = datetime.date(2020, 1, 1)
    end_date = datetime.date.today()
    delta = datetime.timedelta(days=1)

    df_morgenpost = self.fetch_germany_morgenpost()
    
    row_index = 0
    while start_date <= end_date:

      print(start_date.strftime("%Y-%m-%d"))
      for bundesland in df_info['Bundesland']:
        selected_row = df_morgenpost[df_morgenpost['label']==bundesland].loc[df_morgenpost['date'] == str(start_date)]
        if selected_row.shape[0] > 0:
          df_all.at[row_index, f'{bundesland}:morgenpost:confirmed'] = int(selected_row['confirmed'])
          df_all.at[row_index, f'{bundesland}:morgenpost:recovered'] = int(selected_row['recovered'])
          df_all.at[row_index, f'{bundesland}:morgenpost:deaths'] = int(selected_row['deaths'])
        else:
          df_all.at[row_index, f'{bundesland}:morgenpost:confirmed'] = 0
          df_all.at[row_index, f'{bundesland}:morgenpost:recovered'] = 0
          df_all.at[row_index, f'{bundesland}:morgenpost:deaths'] = 0
          
        #print(df_info.loc[df_info['Bundesland'] == bundesland]["Einwohner"])
        #df_all.at[0, f'{bundesland}:info:population'] = int(df_info.loc[df_info['Bundesland'] == bundesland]["Einwohner"])
        #print("Einwohner:", int(df_info.loc[df_info['Bundesland'] == bundesland]["Einwohner"]))
        #df_all.at[row_index, f'{bundesland}:info:population'] = 0#int(df_info.loc[df_info['Bundesland'] == bundesland]["Einwohner"])

      df_all.at[row_index, f'date'] = str(start_date)

      start_date += delta
      row_index += 1

    return df_all


if __name__ == "__main__":
  data_acquisition = DataAcquisition()
  df = data_acquisition.fetch_all_data()
  df.to_csv('dataset.csv', index = False)