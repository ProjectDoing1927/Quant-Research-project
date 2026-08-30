import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def scatter_plot(candle, timeframe, forward_period):
    return_column = f"forward_{forward_period}m_return"

    conditions = [
        ("strong buy delta", "Strong buy delta", "green"),
        ("very strong buy delta", "Very strong buy delta", "limegreen"),
        ("strong sell delta", "Strong sell delta", "red"),
        ("very strong sell delta", "Very strong Sell delta", "#ff0000")]
    figure, graphs = plt.subplots(2, 2, figsize=(15,10), sharex=True, sharey=True)
    # 4 charts, same axis, same scale
    graphs = graphs.flatten()
    #2x2 array to single array
    for graph, condition_information in zip(graphs, conditions):
        #pairs subplots
        condition = condition_information[0]
        chart_title = condition_information[1]
        dot_colour = condition_information[2]
        #set for each condition
        selected_events = candle.loc[candle[condition], [return_column]].dropna()
        graph.scatter(selected_events.index, selected_events[return_column], color=dot_colour, s=15)
        #scatter type
        graph.axhline(y=0, color="black", linewidth=1)
        #0 line
        graph.set_title(f"{chart_title}({len(selected_events)} events)")
        graph.set_xlabel("Date")
        #change to Date 
        graph.set_ylabel("Forward movement (%)")
        graph.grid(alpha=0.2)
    figure.autofmt_xdate()
    plt.tight_layout()
    #stops overlaps
    plt.show()
         #column name, chart title, dot colour
def distribution(candle, timeframe, period):
    PH = "delta"
    delta = candle[PH].dropna()
    forwardPeriod = f"forward_{period}m_return"
    

    figure, graphs = plt.subplots(nrows=2, ncols=1, figsize=(12, 9))
    first = delta.quantile(0.01)
    fifth = delta.quantile(0.05)
    ninety_fifth = delta.quantile(0.95)
    ninety_nine = delta.quantile(0.99)

    graphs[0].hist(delta, bins=500, color="blue", range=(-700, 700))
    #histogram

    graphs[0].axvline(first, color="darkred", label="1st")
    graphs[0].axvline(fifth, color="red", label="5th")
    graphs[0].axvline(ninety_fifth, color="green", label="95th")
    graphs[0].axvline(ninety_nine, color="darkgreen", label="99th")
    graphs.set_title("Raw Delta Distribution of 1 min events")
    graphs[0].set_xlabel("Raw Delta ")
    graphs[0].set_ylabel("Number of Events")
    
    graphs[0].legend(fontsize=12)
    graphs[0].grid(alpha=0.2)
    

    plt.tight_layout()
    plt.show()



def forward_return_distribution(candle, condition):

    periods = [1, 5, 15, 60]

    return_data = []

    for i in periods:

        return_column = f"forward_{i}m_return"

        selected_returns = candle.loc[candle[condition], return_column].dropna()

        return_data.append(selected_returns)

    # Same x-axis range across all four charts
    all_returns = pd.concat(return_data)

    lower_limit = all_returns.quantile(0.005)
    upper_limit = all_returns.quantile(0.995)
    #contain most data

    figure, graphs = plt.subplots(2, 2, figsize=(14, 9), sharex=True)

    graphs = graphs.flatten()

    for i in range(4):

        graph = graphs[i]
        period = periods[i]
        selected_returns = return_data[i]

        mean_return = selected_returns.mean()
        median_return = selected_returns.median()

        graph.hist(selected_returns, bins=100, range=(lower_limit, upper_limit), color="blue")

        # Shows where returns equal zero
        graph.axvline(
            0,
            color="black",
            linewidth=1.2,
            label="Zero return"
        )

        
        

        graph.set_title(
            f"{period}-Minute Forward Returns"
        )

        graph.set_xlabel("Forward return (%)")
        graph.set_ylabel("Number of Events")

        graph.set_xlim(lower_limit, upper_limit)
        #scale

        graph.grid()

        graph.legend(fontsize=8)

    figure.suptitle(f"Distribution of Forward Returns Following {condition.title()}", fontsize=14)

    plt.tight_layout()
    plt.show()
