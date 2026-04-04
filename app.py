import pandas as pd

# Load the data sheet
df = pd.read_csv('A Lister 1.5.xlsx - Sheet1.csv')
number_cols = ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'Bonus']

def backtest_strategy(data, draws_to_check=100):
    hits_log = []
    
    # Iterate through the history
    for i in range(len(data) - draws_to_check - 1, len(data) - 1):
        current_draw = data.iloc[i][number_cols].values
        next_draw = data.iloc[i+1][number_cols].values
        
        # RULE 1: Mirror Rule (50 - x)
        mirrors = [50 - x for x in current_draw]
        
        # RULE 2: Split Rule (Differences between every pair)
        splits = []
        for x in range(len(current_draw)):
            for y in range(x + 1, len(current_draw)):
                diff = abs(current_draw[x] - current_draw[y])
                if 1 <= diff <= 49:
                    splits.append(diff)
        
        # THE CONFIRMATION TEST: Must appear in both Mirrors and Splits
        confirmed_predictions = list(set(mirrors) & set(splits))
        
        # CHECK FOR SUCCESS (Did the confirmed number hit in the next draw?)
        hits = [n for n in confirmed_predictions if n in next_draw]
        
        hits_log.append({
            'Date': data.iloc[i+1]['Date'],
            'Predictions': confirmed_predictions,
            'Actual_Result': next_draw,
            'Hits': hits,
            'Success': len(hits) > 0
        })
        
    return pd.DataFrame(hits_log)

# Run the test
results = backtest_strategy(df)
print(f"Total Success Rate: {results['Success'].mean() * 100:.2f}% of draws had a hit.")
