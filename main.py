'''
 # @ Create Time: 2022-12-06 15:16:27.807534
'''

from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import pandas as pd
import json
import os
import plotly.graph_objects as go

PORT=8081

from plotly.subplots import make_subplots

temp = pd.DataFrame()

test_names = ['cloud-hypervisor-memory-footprint-inside-container', \
        'cloud-hypervisor-memory-footprint', \
        'qemu-memory-footprint-inside-container', \
        'qemu-memory-footprint-ksm', \
        'qemu-memory-footprint']

def collect_file_results_list():
    prefix="memoryFootPrintJob_ws"
    workspace_path ="/home/jenkins/workspace/workspace/"
    results_path="/go/src/github.com/kata-containers/tests/metrics/results/artifacts"

    test_db={}

    for root, dirs, files in os.walk(workspace_path):
        for dir in dirs:

            if prefix in dir:
                for testname in test_names:
                    full_path_testname = os.path.join(root,dir) + results_path +"/" + testname + ".json"

                    if os.path.exists(full_path_testname):

			# make a pair <testname,full_path_testname> and add into test_db
                        test_db.setdefault(testname, []).append(full_path_testname)
    return test_db


# maplist: the map of [resultsName,filePathResults]
# groupname: the key value (name) that points to the group of results
def collect_data_in_dfs(maplist, groupname):
    dfs = [] # empty list used as temporal storage

    # Collect data from the json files in a list of results
    for file in file_results_map[groupname]:
        with open(file,'r') as f:
            data = json.loads(f.read())
            dfs.append(data)

    # normalize the metadata in a dataframe
    metadata = pd.json_normalize(
            dfs,
            meta = ['@timestamp', ['env']],
            errors="ignore")

    # extract the key/value concatenated pair 'Results' key (section)
    key_results_col = [ s for s in metadata if "Results" in s][0]

    if not key_results_col:
        print("Error: key results not found. Exit!")
        exit()

     # Delete duplicated column of results pointed by key_results_match
    del metadata[key_results_col]

    # print ("Key found: ", key_results_match)

    # Remove the value from the key.value pair (testname.Result). hold the key
    test_name_key = key_results_col.split(sep='.', maxsplit=1)[0]
    if not test_name_key:
        print("Error: test name key not found. Exit!")
        exit()

    print ("Sub Key:", test_name_key)

    result = pd.json_normalize(
            dfs,
            record_path = [test_name_key, ['Results']],
            errors="ignore")

    # Joint results and metadata df's
    df1 = pd.concat([result,metadata], axis=1, join="inner")
    return df1

# 1. Remove columns that contains units (i.e. kB, etc)
# 2. Casting column type values
def prepare_df(df):
    for col in df.columns:
        if "Units" in col:
            del df[col]
        elif "Result" in col:
            df[col] = df[col].astype('int64')
    df['date.Date'] = pd.to_datetime(df['date.Date']).dt.date
    df.sort_values(by=['date.Date'], inplace=True)

# file_results_map collects the list of file results, and it is organized by testnames
file_results_map = collect_file_results_list()

# Populate all dataframes with results for:
#   cloud-hypervisor-memory-footprint-inside-container
#   cloud-hypervisor-memory-footprint
#   qemu-memory-footprint-inside-container
#   qemu-memory-footprint

df_clh_inside = collect_data_in_dfs(file_results_map, 'cloud-hypervisor-memory-footprint-inside-container')
df_clh_simple = collect_data_in_dfs(file_results_map, 'cloud-hypervisor-memory-footprint')

df_qemu_inside = collect_data_in_dfs(file_results_map, 'qemu-memory-footprint-inside-container')
df_qemu_simple = collect_data_in_dfs(file_results_map, 'qemu-memory-footprint')

# Compact dataframes
prepare_df(df_clh_inside)
prepare_df(df_qemu_inside)

prepare_df(df_clh_simple)
prepare_df(df_qemu_simple)

# Create two list containing metric labels (keys)
metrics_inside = ['memavailable.Result', 'memrequest.Result', 'memfree.Result']
metrics_simple = ['average.Result', 'virtiofsds.Result', 'shims.Result', 'qemus.Result']

# Add main title of the dashboard
app = Dash(__name__, title="Kata Containers Dashboard")

# Prepare Figures

# Fig CLH vs QEMU Average Results
fig_ch_qemu_average = go.Figure()

fig_ch_qemu_average.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df_clh_simple[metrics_simple[0]],
    name='avg_clh',
    mode="markers+lines"
))

fig_ch_qemu_average.add_trace(go.Scatter(
    x=df_qemu_simple['date.Date'], y=df_qemu_simple[metrics_simple[0]],
    name='avg_qemu',
    mode="markers+lines"
))

# Fig CLH vs QEMU virtiofsds results
fig_ch_qemu_virtiofsds = go.Figure()

fig_ch_qemu_virtiofsds.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df_clh_simple[metrics_simple[1]],
    name="virtiofsds_clh",
    mode="markers+lines"
))

fig_ch_qemu_virtiofsds.add_trace(go.Scatter(
    x=df_qemu_simple['date.Date'], y=df_qemu_simple[metrics_simple[1]],
    name='virtiofsds_qemu',
    mode="markers+lines"
))

# Fig CLH vs QEMU shims results
fig_ch_qemu_shims = go.Figure()

fig_ch_qemu_shims.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df_clh_simple[metrics_simple[2]],
    name="shims_clh",
    mode="markers+lines",
))

fig_ch_qemu_shims.add_trace(
    go.Scatter(x=df_qemu_simple['date.Date'], y=df_qemu_simple[metrics_simple[2]],
    name="shims_qemu",
    mode="markers+lines",
))

# Fig CLH vs QEMU memfree results
fig_ch_qemu_qemus = go.Figure()

fig_ch_qemu_qemus.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df_clh_simple[metrics_simple[3]],
    name="qemus_clh",
    mode="markers+lines",
))

fig_ch_qemu_qemus.add_trace(go.Scatter(
    x=df_qemu_simple['date.Date'], y=df_qemu_simple[metrics_simple[3]],
    name="qemus_qemu",
    mode="markers+lines",
))

# Fig CLH vs QEMU memavailable results (inside container)
fig_ch_qemu_memavail = go.Figure()

fig_ch_qemu_memavail.add_trace(go.Scatter(
    x=df_clh_inside['date.Date'], y=df_clh_inside[metrics_inside[0]],
    name="mem_avail_clh",
    mode="markers+lines",
))

fig_ch_qemu_memavail.add_trace(go.Scatter(
    x=df_qemu_inside['date.Date'], y=df_qemu_inside[metrics_inside[0]],
    name="mem_avail_qemu",
    mode="markers+lines",
))

# Fig CLH vs QEMU memrequest results (inside container)
fig_ch_qemu_memreq = go.Figure()

fig_ch_qemu_memreq.add_trace(go.Scatter(
    x=df_clh_inside['date.Date'], y=df_clh_inside[metrics_inside[1]],
    name="memreq_clh",
    mode="markers+lines",
))

fig_ch_qemu_memreq.add_trace(go.Scatter(
    x=df_qemu_inside['date.Date'], y=df_qemu_inside[metrics_inside[1]],
    name="memreq_qemu",
    mode="markers+lines",
))


# Fig CLH vs QEMU memfree results (inside container)
fig_ch_qemu_memfree = go.Figure()

fig_ch_qemu_memfree.add_trace(go.Scatter(
    x=df_clh_inside['date.Date'], y=df_clh_inside[metrics_inside[2]],
    name="memfree_clh",
    mode="markers+lines",
))

fig_ch_qemu_memfree.add_trace(go.Scatter(
    x=df_qemu_inside['date.Date'], y=df_qemu_inside[metrics_inside[2]],
    name="memfree_qemu",
    mode="markers+lines",
))


app.layout = html.Div(children=[
    html.H1(children='Kata Memory Footprint Dashboard'),

    html.H2(children=str(metrics_simple[0] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id='qemu_vs_clh_average',
        figure=fig_ch_qemu_average
    ),

    html.H2(children=str(metrics_simple[1] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_simple[1]),
        figure=fig_ch_qemu_virtiofsds
    ),

    html.H2(children=str(metrics_simple[2] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_simple[2]),
        figure=fig_ch_qemu_shims
    ),

    html.H2(children=str(metrics_simple[3] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_simple[3]),
        figure=fig_ch_qemu_qemus
    ),

    html.H2(children=str(metrics_inside[0] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_inside[0]),
        figure=fig_ch_qemu_memavail
    ),

    html.H2(children=str(metrics_inside[1] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_inside[1]),
        figure=fig_ch_qemu_memreq
    ),

    html.H2(children=str(metrics_inside[2] + " CLH vs QEMU"), style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_inside[2]),
        figure=fig_ch_qemu_memfree
    ),

])

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=PORT, debug=True)
