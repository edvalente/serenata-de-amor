
# coding: utf-8

# # Doublechecking net values
# 
# Some people have been [reporting problems](https://github.com/datasciencebr/serenata-de-amor/issues/85) in the value of `net_value` column in the CEAP datasets. It doesn't seem to really match what it should contain.

# In[1]:

import pandas as pd
import numpy as np

filenames = ['../data/2016-08-08-current-year.xz',
             '../data/2016-08-08-last-year.xz',
             '../data/2016-08-08-previous-years.xz']
dataset = pd.DataFrame()

for filename in filenames:
    data = pd.read_csv(filename,
                       parse_dates=[16],
                       dtype={'document_id': np.str,
                              'congressperson_id': np.str,
                              'congressperson_document': np.str,
                              'term_id': np.str,
                              'cnpj_cpf': np.str,
                              'reimbursement_number': np.str})
    dataset = pd.concat([dataset, data])


# In[2]:

len(dataset)


# In[3]:

dataset['issue_date'] = pd.to_datetime(dataset['issue_date'], errors='coerce')


# In[4]:

(dataset['document_value'].isnull()).sum()


# In[5]:

dataset[dataset['document_value'].isnull()]


# In[6]:

dataset[dataset['document_value'].isnull()].iloc[0]


# Since we expect precision in our `net_value` calculation, I'm going to use integers and not floats.

# In[7]:

import math

dataset = dataset.dropna(subset=['document_value'])
dataset['document_value_int'] = (dataset['document_value'] * 100.).apply(math.ceil).astype(np.int)
dataset['remark_value_int'] = (dataset['remark_value'] * 100.).apply(math.ceil).astype(np.int)
dataset['net_value_int'] = (dataset['net_value'] * 100.).apply(math.ceil).astype(np.int)
dataset['calc_net_value_int'] = dataset['document_value_int'] - dataset['remark_value_int']


# In[8]:

((dataset['calc_net_value_int'] - dataset['net_value_int']) != 0).sum()


# In[9]:

dataset.iloc[0]


# In[10]:

dataset['diff_net_value'] = dataset['net_value_int'] - dataset['calc_net_value_int']
dataset.loc[dataset['diff_net_value'] != 0, 'diff_net_value'].describe()


# What's the number of records with distinct values of `net_value` and our own `net_value`, considering acceptable a maximum difference of 2 cents?

# In[11]:

with_significant_difference = dataset.loc[dataset['diff_net_value'].abs() > 2]


# In[12]:

with_significant_difference['subquota_description'].describe()


# It's not just a single subquota, but almost all of them. Probably means that there's something intrinsic in the dataset we still don't know. 

# In[13]:

print(len(dataset['subquota_description'].unique()))
print(len(with_significant_difference['subquota_description'].unique()))


# In[14]:

from altair import *

Chart(with_significant_difference).mark_bar().encode(
    x=X('subquota_description:O',
        sort=SortField(field='subquota_description',
                       order='descending',
                       op='count')),
    y='count(*):Q',
)


# In[15]:

with_significant_difference['subquota_description'].unique()


# I want to perform a further investigation in flight ticket issues, since [it's already documented](http://jarbas.datasciencebr.com/static/ceap-datasets.html) that `net_value`'s may be negative given canceled flights.

# In[16]:

flight_ticket_issues = with_significant_difference['subquota_description'] == 'Flight ticket issue'
with_significant_difference.loc[flight_ticket_issues, 'net_value'].head(10)


# Here we have 3 documents with `reimbursement_number` equal to zero. How about disconsidering them to start? If there's no `reimbursement_number`, we could assume that no reimbursement happened (if the data says data, the Chamber of Deputies should be contacted to confirm the affirmation).

# In[17]:

with_significant_difference.loc[flight_ticket_issues &                                 (with_significant_difference['congressperson_id'] == '178983')]


# In[18]:

dataset['reimbursement_number'] =     dataset['reimbursement_number'].replace('0', None)
dataset = dataset.dropna(subset=['reimbursement_number'])


# In[19]:

dataset['document_id'].isnull().sum()


# In[20]:

with_significant_difference = dataset.loc[dataset['diff_net_value'].abs() > 2]
len(with_significant_difference)


# In[21]:

flight_ticket_issues = with_significant_difference['subquota_description'] == 'Flight ticket issue'
with_significant_difference.loc[flight_ticket_issues].head()


# In[22]:

with_significant_difference.loc[flight_ticket_issues].iloc[0]


# In[23]:

dataset[(dataset['congressperson_name'] == 'CLARISSA GAROTINHO') &         (dataset['month'] == 4) &         (dataset['year'] == 2016) &         (dataset['subquota_description'] == 'Flight ticket issue')]['net_value_int'].sum()


# In[24]:

dataset.loc[dataset['document_number'] == 'Bilhete: VHVK6G']


# In[25]:

dataset.loc[dataset['document_number'] == 'Bilhete: VHVK6G'].iloc[0]


# In[26]:

dataset.loc[dataset['document_number'] == 'Bilhete: VHVK6G'].iloc[1]


# In[27]:

dataset.loc[dataset['document_number'] == 'Bilhete: VHVK6G'].iloc[2]


# The dataset contains multiple records for the same `document_number`. In this case, they correspond to multiple flight tickets to the same flight, but for distinct passengers.

# In[28]:

dataset.loc[dataset['document_number'] == 'Bilhete: VHVK6G',
            ['document_value_int', 'remark_value_int', 'document_number', 'reimbursement_number', 'passenger', 'net_value_int', 'calc_net_value_int']]


# http://jarbas.datasciencebr.com/#/document_id/5914504
# 
# These documents seem to correspond to the same receipt. The reimbursements were claimed in the same `batch_number` but in distinct reimbursements (`reimbursement_number`).
# 
# Together, `document_value`, `remark_value` and `net_value` make sense.

# In[29]:

with_significant_difference[with_significant_difference['document_id'] == '5914504']


# The Chamber of Deputies just use `applicant_id`, `year` and `document_id` when refering to a reimbursement. If all of them together count as a single reimbursement, an expense is an aggregation of all rows with the same above. attributes.
# 
# Let's prove the affirmation above analysing the whole dataset and checking if the values make more sense after.

# In[30]:

data_with_id = dataset[(~dataset['document_id'].isnull()) &
                       (~dataset['year'].isnull()) &
                       (~dataset['applicant_id'].isnull())]


# In[ ]:

keys = ['applicant_id', 'year', 'document_id']
grouped = data_with_id.groupby(keys)
len(grouped)


# In[ ]:

reimbursement_numbers = grouped['reimbursement_number'].agg(lambda x: ','.join(set(x))).reset_index()
agg_net_values_int = grouped['net_value_int'].agg(np.sum).reset_index()


# In[ ]:

agg_net_values_int.head()


# In[ ]:

agg_data = pd.merge(pd.merge(reimbursement_numbers, agg_net_values_int, on=keys),
                    data_with_id,
                    on=keys,
                    suffixes=('', '_from_original'))
agg_data.head()


# There are 2,072,559 documents in the datasets, but when considering just the combination of non-empty values for `applicant_id`, `year` and `document_id`, half of that is found. In other words, the CEAP seem to have paid for about 1MM expenses so far.

# In[ ]:

len(agg_data)


# In[ ]:

agg_data.drop_duplicates(subset=keys, inplace=True)

len(agg_data)


# In[ ]:

agg_data.drop(['reimbursement_number_from_original',
               'net_value_int_from_original'],
              axis=1,
              inplace=True)


# In[ ]:

agg_data['document_value_int'] = (agg_data['document_value'] * 100.).apply(math.ceil).astype(np.int)
agg_data['remark_value_int'] = (agg_data['remark_value'] * 100.).apply(math.ceil).astype(np.int)
# agg_data['net_value_int'] = (agg_data['net_value'] * 100.).apply(math.ceil).astype(np.int)
agg_data['calc_net_value_int'] = agg_data['document_value_int'] - agg_data['remark_value_int']
agg_data['diff_net_value'] = agg_data['net_value_int'] - agg_data['calc_net_value_int']


# In[ ]:

with_significant_difference = agg_data.loc[agg_data['diff_net_value'].abs() > 2]


# Disconsidering multiple records with this same combination, just 744 remain with a large difference between our own calculation of `net_value`s and the value directly in the original dataset.

# In[ ]:

len(with_significant_difference)


# The majority of records were explained by the previous test, having all the flight ticket issues disappeared (though a few "Flight tickets" remain).

# In[ ]:

Chart(with_significant_difference).mark_bar().encode(
    x=X('subquota_description:O',
        sort=SortField(field='subquota_description',
                       order='descending',
                       op='count')),
    y='count(*):Q',
)


# In[ ]:

agg_data[agg_data['reimbursement_number'].str.contains(',')]


# The document with major positive difference in the dataset doesn't seem to have any irregularity. The deputy asked the reimbursement for R\$ 25.000,00, but received just R\$ 6.376,11.

# In[ ]:

with_significant_difference.sort_values('diff_net_value').iloc[0]


# Deputies receiving less money than they asked is OK. What if they are receiving more than they should (values in the `document_value` column)?

# In[ ]:

has_extra_reimbursement = with_significant_difference['diff_net_value'] > 0
extra_reimbursement = with_significant_difference[has_extra_reimbursement].     sort_values('diff_net_value', ascending=False)
len(extra_reimbursement)


# In[ ]:

extra_reimbursement.head()


# In[ ]:

Chart(extra_reimbursement).mark_bar().encode(
    x=X('subquota_description:O',
        sort=SortField(field='subquota_description',
                       order='descending',
                       op='count')),
    y='count(*):Q',
)


# In[ ]:

extra_reimbursement.sort_values('diff_net_value', ascending=False).iloc[0]


# This document says that a deputy received R\$ 3.226,59 more than it should. Let's check all the datasets we have to see if there's any mistake in the calculation.

# In[ ]:

dataset[dataset['document_id'] == '5951638']


# In[ ]:

data_with_id[data_with_id['document_id'] == '5951638']


# In[ ]:

extra_reimbursement[extra_reimbursement['document_id'] == '5951638']


# In[ ]:

extra_reimbursement[extra_reimbursement['document_id'] == '5951638'].iloc[0]


# Doesn't seem to have. Calculations are doing what it's expected and are following our understanding of the dataset.
# 
# There's a possibility that this extra payment counted towards other requests for reimbursements. Let's check.

# In[ ]:

dataset[(dataset['applicant_id'] == 2899) &         (dataset['subquota_number'] == 3) &         (dataset['year'] == 2016) &         (dataset['month'].isin([1, 2, 3]))]


# Can't see anything proving that. Going to analize the next reimbursement.

# In[ ]:

extra_reimbursement.sort_values('diff_net_value', ascending=False).iloc[1]


# In[ ]:

(extra_reimbursement['remark_value'] > 0).sum()


# Nope. Not a clue.

# In[ ]:

extra_reimbursement.sort_values('diff_net_value', ascending=False).iloc[2]


# Not yet.

# In[ ]:

extra_reimbursement.sort_values('diff_net_value', ascending=False).iloc[3]


# In[ ]:



