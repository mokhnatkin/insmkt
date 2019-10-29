#plots various types of graphs

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from flask import Response


def plot_linear_graph(labels,values,values_l_y,label1,label2,show_last_year,annotate,title):#plot linear graph
    fig, ax = plt.subplots()
    ax.plot(labels, values, label=label1)
    if annotate:#annotate graphs
        for i,j in zip(labels,values):
            ax.annotate(str(j),xy=(i,j))
    ax.set_title(title)    
    if show_last_year:
        ax.plot(labels, values_l_y, label=label2)
        ax.legend(loc='upper left')
        if annotate:
            for i,j in zip(labels,values_l_y):
                ax.annotate(str(j),xy=(i,j))
    fig.autofmt_xdate()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')    