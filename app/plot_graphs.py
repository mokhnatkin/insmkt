#plots various types of graphs


from flask import Response
import matplotlib
matplotlib.use('Agg')
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


def plot_linear_graph(labels,_values,_values_l_y,label1,label2,show_last_year,annotate,title):#plot linear graph
   # Generate the figure **without using pyplot**.
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.subplots()
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
    # Save it to a temporary buffer.
    output = io.BytesIO()
    canvas.print_png(output)

    return Response(output.getvalue(), mimetype='image/png')


def plot_barchart(labels,_values,_values_l_y,title,ylabel,show_last_year,label1,label2):#plot bar chart
    def autolabel(rects):
        #Attach a text label above each bar in *rects*, displaying its height.
        for rect in rects:
            height = rect.get_height()
            ax.annotate('{}'.format(height),
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
    
    values = np.array(_values)
    ind = np.arange(len(values))  # the x locations for the groups
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.subplots()

    if show_last_year:
        values_l_y = np.array(_values_l_y)
        w = 0.35
        rects1 = ax.bar(ind, values, w, label=label1)
        rects2 = ax.bar(ind + w, values_l_y, w, label=label2)
        ax.set_xticks(ind + 0.5*w)
        ax.set_xticklabels(labels,rotation=90)
        ax.legend(loc='best')
    else:
        w = 0.7
        rects1 = ax.bar(ind, values, w)
        ax.set_xticks(ind)
        ax.set_xticklabels(labels)
        
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    autolabel(rects1)
    fig.autofmt_xdate()
    if show_last_year:
        autolabel(rects2)
    
    output = io.BytesIO()
    canvas.print_png(output)
    
    return Response(output.getvalue(), mimetype='image/png')

#plot_scatter(_x,_y,title,labels,xlabel,ylabel)
def plot_scatter(_x,_y,title,labels=None,xlabel=None,ylabel=None):#scatter plot
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.subplots()
    x = np.array(_x)
    y = np.array(_y)
    ax.scatter(x, y)
    ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if labels is not None:
        for i, txt in enumerate(labels):
            ax.annotate(txt, (x[i], y[i]))
    output = io.BytesIO()
    canvas.print_png(output)

    return Response(output.getvalue(), mimetype='image/png')


def plot_piechart(labels,_values,title):#pie chart    
    values = np.array(_values)
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax = fig.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    ax.set_title(title)
    output = io.BytesIO()
    canvas.print_png(output)
    
    return Response(output.getvalue(), mimetype='image/png')





