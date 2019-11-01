#plots various types of graphs

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from flask import Response
import numpy as np
from matplotlib.figure import Figure


def plot_linear_graph(labels,values,values_l_y,label1,label2,show_last_year,annotate,title):#plot linear graph
    #fig, ax = plt.subplots()
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(111)
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
    plt.clf()
    return Response(output.getvalue(), mimetype='image/png')


def plot_barchart(labels,values,values_l_y,title,ylabel,show_last_year,label1,label2):#plot bar chart
    ind = np.arange(len(values))  # the x locations for the groups
    fig, ax = plt.subplots()
    
    if not show_last_year:
        w = 0.75
        ax.bar(ind, values, w)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_xticks(ind)
        ax.set_xticklabels(labels)
    else:
        w = 0.35
        opacity = 0.8
        plt.bar(ind, values, w, alpha=opacity,color='b',label=label1)
        plt.bar(ind + w, values_l_y, w, alpha=opacity,color='g',label=label2)        
        plt.ylabel(ylabel)
        plt.title(title)
        plt.xticks(ind + w, labels)
        plt.legend()
        plt.tight_layout()    
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    
    return Response(output.getvalue(), mimetype='image/png')


def plot_piechart(labels,values,title):#pie chart
    #fig, ax = plt.subplots()
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(111)    
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    ax.set_title(title)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    plt.clf()
    return Response(output.getvalue(), mimetype='image/png')



    
    
    
    