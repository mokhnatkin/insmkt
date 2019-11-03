#plots various types of graphs

import matplotlib
matplotlib.use('Agg')#matplotlib.use('PS')
import matplotlib.style as mplstyle
mplstyle.use('fast')#speed optimization
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from flask import Response
import numpy as np


def plot_linear_graph(labels,_values,_values_l_y,label1,label2,show_last_year,annotate,title):#plot linear graph
    fig, ax = plt.subplots()
    values = np.array(_values)
    ax.plot(labels, values, label=label1)
    if annotate:#annotate graphs
        for i,j in zip(labels,values):
            ax.annotate(str(j),xy=(i,j))
    ax.set_title(title)    
    if show_last_year:
        values_l_y = np.array(_values_l_y)
        ax.plot(labels, values_l_y, label=label2)
        ax.legend(loc='best')
        if annotate:
            for i,j in zip(labels,values_l_y):
                ax.annotate(str(j),xy=(i,j))
    fig.autofmt_xdate()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)    
    return Response(output.getvalue(), mimetype='image/png')


def plot_barchart(labels,_values,_values_l_y,title,ylabel,show_last_year,label1,label2):#plot bar chart
    def autolabel(rects):
        """Attach a text label above each bar in *rects*, displaying its height."""
        for rect in rects:
            height = rect.get_height()
            ax.annotate('{}'.format(height),
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    values = np.array(_values)
    ind = np.arange(len(values))  # the x locations for the groups
    fig, ax = plt.subplots()    
    if show_last_year:
        values_l_y = np.array(_values_l_y)
        w = 0.35
        rects1 = plt.bar(ind, values, w, label=label1)
        rects2 = plt.bar(ind + w, values_l_y, w, label=label2)
        plt.xticks(ind + w, labels)
        plt.legend(loc='best')
    else:
        w = 0.7
        rects1 = plt.bar(ind, values, w)
        plt.xticks(ind, labels)    
    plt.ylabel(ylabel)
    plt.title(title)
    autolabel(rects1)
    if show_last_year:
        autolabel(rects2)
    plt.tight_layout()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    
    return Response(output.getvalue(), mimetype='image/png')


def plot_piechart(labels,values,title):#pie chart
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    ax.set_title(title)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')



    
    
    
    