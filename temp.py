import pandas as pd
population_csv = 'data/pop.csv'
population_df = pd.read_csv(population_csv, sep=';')
print(population_df.head())