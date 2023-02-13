'''
 # @ Create Time: 2022-12-06 15:16:27.807534
'''

from dash import Dash, html, dcc, Input, Output
import pandas as pd
import json
import os
import plotly.graph_objects as go
from humanfriendly import format_size

# experiment
# import plotly.express as px
import numpy as np

PORT=8081

# for testing
from plotly.subplots import make_subplots

temp = pd.DataFrame()

test_names = ['cloud-hypervisor-memory-footprint-inside-container', \
        'cloud-hypervisor-memory-footprint', \
        'cloud-hypervisor-boot-times', \
        'cloud-hypervisor-blogbench', \
        'qemu-memory-footprint-inside-container', \
        'qemu-memory-footprint-ksm', \
        'qemu-memory-footprint', \
        'qemu-boot-times', \
        'qemu-blogbench'
]

def collect_file_results_list():
    prefixes_list = ["jenkins-memoryFootPrintJob-", "boottimes", "blogbench"]
    workspace_path = "/home/kata/dashboard-db/"
    results_path = "artifacts"

    test_db={}

    # we shall store all the file names in this list
    filelist = []

    for root, dirs, files in os.walk(workspace_path):
        for dir in dirs:
            for prefix in prefixes_list:

                if prefix in dir:

                    for testname in test_names:

                        full_path_testname = os.path.join(root,dir) + "/" + results_path +"/" + testname + ".json"

                        if os.path.exists(full_path_testname):

            	    		# build a pair <testname,full_path_testname> inside test_db
                            filelist.append(full_path_testname)
                            test_db.setdefault(testname, []).append(full_path_testname)
    return test_db

'''
 @maplist: the map of [resultsName,filePathResults]
 @groupname: the key value (name) that points to the group of results
'''

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

    result = pd.json_normalize(
            dfs,
            record_path = [test_name_key, ['Results']],
            errors="ignore")

    # Joint results and metadata df's
    df1 = pd.concat([result,metadata], axis=1, join="inner")
    return df1

# 1. Remove columns that contains units (i.e. kB, etc)
# 2. Casting column type values
# Todo: return a map list of untis
def prepare_df(df):
    skip_items=['total.Result']

    for col in df.columns:
        if "Units" in col:
            del df[col]
        elif "Result" in col:
            df[col] = df[col].astype('float64')
            # ToDo:  write results in bytes
            if not col in skip_items:
                df[col] = df[col].apply(lambda x: x*1000)

    df['date.Date'] = pd.to_datetime(df['date.Date']).dt.date
    df.sort_values(by=['date.Date'], inplace=True)


def prepare_df_blog_bench(df):
    key_headers=['read.Result', 'write.Result', 'Nb blogs.Result']

    for col in df.columns:
        if col in key_headers:

            # Split only the object items that contains strings 
            # that consist of an array of int's in csv format
            if not df[col].dtype == 'int64':
                df[col] = df[col].str.split()

    df['date.Date'] = pd.to_datetime(df['date.Date']).dt.date
    df.sort_values(by=['date.Date'], inplace=True)


# file_results_map collects the list of file results, and it is organized by testnames
file_results_map = collect_file_results_list()

# Populate the dataframe with results from each test
df_clh_mem_inside = collect_data_in_dfs(file_results_map, 'cloud-hypervisor-memory-footprint-inside-container')
df_clh_simple = collect_data_in_dfs(file_results_map, 'cloud-hypervisor-memory-footprint')
df_clh_boot = collect_data_in_dfs(file_results_map, 'cloud-hypervisor-boot-times')
df_clh_blogbench  = collect_data_in_dfs(file_results_map, 'cloud-hypervisor-blogbench')

df_qemu_inside = collect_data_in_dfs(file_results_map, 'qemu-memory-footprint-inside-container')
df_qemu_simple = collect_data_in_dfs(file_results_map, 'qemu-memory-footprint')
df_qemu_boot = collect_data_in_dfs(file_results_map, 'qemu-boot-times')
df_qemu_blogbench = collect_data_in_dfs(file_results_map, 'qemu-blogbench')

# remove unused columns

prepare_df(df_clh_mem_inside)
prepare_df(df_clh_simple)
prepare_df(df_clh_boot)
prepare_df_blog_bench(df_clh_blogbench)

prepare_df(df_qemu_inside)
prepare_df(df_qemu_simple)
prepare_df(df_qemu_boot)
prepare_df_blog_bench(df_qemu_blogbench)

# Metric labels (keys)
metrics_inside = ['memavailable.Result', 'memrequest.Result', 'memfree.Result']
metrics_simple = ['average.Result', 'virtiofsds.Result', 'shims.Result', 'qemus.Result']
metrics_boot = ['total.Result']
metrics_blogbench = ['write.Result' , 'read.Result']

metrics_simple_titles = ['mem usage for the sum of components: CLH vs QEMU',
    'Virtiofsd mem footprint CLH vs QEMU',
    'Shim footprint CLH vs QEMU',
    'Hypervisor footprint CLH vs QEMU'
]

metrics_inside_titles = ['mem available: CLH vs QEMU',
    'memory requested at startup: CLH vs QEMU',
    'mem free: CLH vs QEMU'
]

metrics_boot_titles = ['Boot time (s) CLH vs QEMU (LIB)']

metrics_blogbench_titles = ['Blogbench write result (number of items) CLH vs QEMU',
    'Blogbench read result (number of items) CLH vs QEMU'
]


# position for each chart title
TITLE_XPOS=0.5

app = Dash(__name__, title="Kata Containers Dashboard")

# Prepare Figures


# Fig CLH vs QEMU Average Results
fig_ch_qemu_average = go.Figure()

df = df_clh_simple
fig_ch_qemu_average.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_simple[0]],
    name='avg_clh',
    mode="markers+lines",
    text=df[metrics_simple[0]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Sum (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

df = df_qemu_simple

fig_ch_qemu_average.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_simple[0]],
    name='avg_qemu',
    mode="markers+lines",
    text=df[metrics_simple[0]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Sum (QEMU): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

fig_ch_qemu_average.update_layout(title_text=metrics_simple_titles[0], title_x=TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")


# Fig CLH vs QEMU virtiofsd results
fig_ch_qemu_virtiofsds = go.Figure()

fig_ch_qemu_virtiofsds.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df_clh_simple[metrics_simple[1]],
    name="virtiofsds_clh",
    mode="markers+lines",
    text=df_clh_simple[metrics_simple[1]],
    customdata = np.stack( (df_clh_simple['env.RuntimeVersion'], df_clh_simple['env.RuntimeCommit'], df_clh_simple['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>virtiofsd (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

fig_ch_qemu_virtiofsds.add_trace(go.Scatter(
    x=df_qemu_simple['date.Date'], y=df_qemu_simple[metrics_simple[1]],
    name='virtiofsds_qemu',
    mode="markers+lines",
    text=df_qemu_simple[metrics_simple[1]],
    customdata = np.stack( (df_qemu_simple['env.RuntimeVersion'], df_qemu_simple['env.RuntimeCommit'], df_qemu_simple['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>virtiofsd (QEMU): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

fig_ch_qemu_virtiofsds.update_layout(title_text=metrics_simple_titles[1], title_x=TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")

# Fig CLH vs QEMU shims results
fig_ch_qemu_shims = go.Figure()

df = df_clh_simple
fig_ch_qemu_shims.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df[metrics_simple[2]],
    name="shims_clh",
    mode="markers+lines",
    text=df[metrics_simple[2]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Shim (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

df = df_qemu_simple
fig_ch_qemu_shims.add_trace(
    go.Scatter(x=df['date.Date'], y=df[metrics_simple[2]],
    name="shims_qemu",
    mode="markers+lines",
    text=df[metrics_simple[2]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Shim (QEMU): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))
fig_ch_qemu_shims.update_layout(title_text=metrics_simple_titles[2], title_x=TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")

# Fig CLH vs QEMU qemu component results
fig_hypervisors_mem = go.Figure()

df = df_clh_simple

fig_hypervisors_mem.add_trace(go.Scatter(
    x=df_clh_simple['date.Date'], y=df[metrics_simple[3]],
    name="qemus_clh",
    mode="markers+lines",
    text=df[metrics_simple[3]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>qemu component (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

df = df_qemu_simple

fig_hypervisors_mem.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_simple[3]],
    name="qemus_qemu",
    mode="markers+lines",
    text=df[metrics_simple[3]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>qemu component (QEMU): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>",
))

fig_hypervisors_mem.update_layout(title_text=metrics_simple_titles[3], title_x=TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")



# Fig CLH vs QEMU memavailable results (inside container)
fig_ch_qemu_memavail = go.Figure()

df = df_clh_mem_inside

fig_ch_qemu_memavail.add_trace(go.Scatter(
    x=df_clh_mem_inside['date.Date'], y=df[metrics_inside[0]],
    name="mem_avail_clh",
    mode="markers+lines",
    text=df[metrics_inside[0]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Mem Available (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

df = df_qemu_inside

fig_ch_qemu_memavail.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_inside[0]],
    name="mem_avail_qemu",
    mode="markers+lines",
    text=df[metrics_inside[0]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Mem Available (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

fig_ch_qemu_memavail.update_layout(title_text=metrics_inside_titles[0], title_x=TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")


# Fig CLH vs QEMU memrequest results (inside container)
fig_ch_qemu_memreq = go.Figure()

df = df_clh_mem_inside
fig_ch_qemu_memreq.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_inside[1]],
    name="memreq_clh",
    mode="markers+lines",
    text=df[metrics_inside[1]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Mem Requested (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

df = df_qemu_inside
fig_ch_qemu_memreq.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_inside[1]],
    name="memreq_qemu",
    mode="markers+lines",
    text=df[metrics_inside[1]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Mem Requested (QEMU): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))


fig_ch_qemu_memreq.update_layout(title_text=metrics_inside_titles[1], title_x=TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")

# Fig CLH vs QEMU memfree results (inside container)
fig_ch_qemu_memfree = go.Figure()

df = df_clh_mem_inside

fig_ch_qemu_memfree.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_inside[2]],
    name="memfree_clh",
    mode="markers+lines",
    text=df[metrics_inside[2]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Mem Free (CLH): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

df = df_qemu_inside

fig_ch_qemu_memfree.add_trace(go.Scatter(
    x=df['date.Date'], y=df[metrics_inside[2]],
    name="memfree_qemu",
    mode="markers+lines",
    text=df[metrics_inside[2]],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Mem Free (QEMU): %{text} bytes</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

fig_ch_qemu_memfree.update_layout(title_text = metrics_inside_titles[2], title_x = TITLE_XPOS,yaxis_tickformat = '.4s', hovermode="x unified")

# Fig CLH vs QEMU boot time results
fig_ch_qemu_boot = go.Figure()

df = df_clh_boot

fig_ch_qemu_boot.add_trace(go.Scatter(
    x=df['date.Date'], y=df['total.Result'],
    name="boot_clh",
    mode="markers+lines",
    text=df['total.Result'],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>boot time (CLH): %{text} secs</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

df = df_qemu_boot

fig_ch_qemu_boot.add_trace(go.Scatter(
    x=df['date.Date'], y=df['total.Result'],
    name="boot_qemu",
    mode="markers+lines",
    text=df['total.Result'],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>boot time (QEMU): %{text} secs</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

fig_ch_qemu_boot.update_layout(title_text = metrics_boot_titles[0], title_x = TITLE_XPOS, yaxis_tickformat = '.4s', hovermode="x unified")


# Fig CLH vs QEMU write blogbench results

fig_ch_qemu_blogbench = go.Figure()

df = df_clh_blogbench

fig_ch_qemu_blogbench.add_trace(go.Scatter(
   x=df['date.Date'], y=df['write.Result'],
    name="write_blogbench_clh",
    mode="markers+lines",
    text=df['write.Result'],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Blogbench write (CLH): %{text} items</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor Ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

df = df_qemu_blogbench

fig_ch_qemu_blogbench.add_trace(go.Scatter(
    x=df['date.Date'], y=df['write.Result'],
    name="write_blogbench_qemu",
    mode="markers+lines",
    text=df['write.Result'],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Blogbench write (qemu): %{text} items</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

fig_ch_qemu_blogbench.update_layout(title_text = metrics_blogbench_titles[0], title_x = TITLE_XPOS, yaxis_tickformat = '.4s')

# Fig CLH vs QEMU read blogench results
fig_ch_qemu_readblogbench = go.Figure()

df = df_clh_blogbench

fig_ch_qemu_readblogbench.add_trace(go.Scatter(
    x=df['date.Date'], y=df['read.Result'],
    name="read_blogbench_clh",
    mode="markers+lines",
    text=df['read.Result'],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Blogbench read (CLH): %{text} items</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

df = df_qemu_blogbench
fig_ch_qemu_readblogbench.add_trace(go.Scatter(
    x=df['date.Date'], y=df['read.Result'],
    name="read_blogbench_qemu",
    mode="markers+lines",
    text=df['read.Result'],
    customdata = np.stack( (df['env.RuntimeVersion'], df['env.RuntimeCommit'], df['env.HypervisorVersion']), axis=-1),
    hovertemplate=
        "<b>Blogbench read (QEMU): %{text} items</b><br><br>" +
        "Runtime: %{customdata[0]}<br>" +
        "Runtime Commit: %{customdata[1]}<br>" +
        "Hypervisor ver.: %{customdata[2]}<br>" +
        "<extra></extra>"
))

fig_ch_qemu_readblogbench.update_layout(title_text=metrics_blogbench_titles[1], title_x=TITLE_XPOS, yaxis_tickformat = '.4s')


app.layout = html.Div(children=[
    html.H1(children='Kata Dashboard'),

    html.H2(children="Memory Usage by kata component", style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_simple[0]),
        figure=fig_ch_qemu_average
    ),

    dcc.Graph(
        id=str(metrics_simple[3]),
        figure=fig_hypervisors_mem
    ),

    dcc.Graph(
        id=str(metrics_simple[1]),
        figure=fig_ch_qemu_virtiofsds
    ),

    dcc.Graph(
        id=str(metrics_simple[2]),
        figure=fig_ch_qemu_shims
    ),

    html.H2(children="Memory Usage inside the container", style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_inside[0]),
        figure=fig_ch_qemu_memavail
    ),

    dcc.Graph(
        id=str(metrics_inside[1]),
        figure=fig_ch_qemu_memreq
    ),

    dcc.Graph(
        id=str(metrics_inside[2]),
        figure=fig_ch_qemu_memfree
    ),

    html.H2(children="Boot times", style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_boot[0]),
        figure=fig_ch_qemu_boot
    ),

    html.H2(children="Blogbench", style={'textAlign': 'center'}),

    dcc.Graph(
        id=str(metrics_blogbench[0]),
        figure=fig_ch_qemu_blogbench
    ),

    dcc.Graph(
        id=str(metrics_blogbench[1]),
        figure=fig_ch_qemu_readblogbench
    ),
])

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=PORT, debug=True)
