
def fix_bars(bars : list):
    '''
    Function takes a list of bar ranges: e.g. [(1, 2), (2, 4), (5, 6)] and 
    combines the ranges so there is no overlap: [(1, 4), (5, 6)]. This function
    could probably be better written. It seems to be working as expected.
    @author: sjkrol

    Args:
        bars (list): a list of bar ranges.
    Returns:
        list: a combined list of bar ranges.
    '''

    bars.sort(key=lambda x: -x[0])
    i = len(bars) - 1

    final_bars = []

    while i > 0:

        current_range = bars[i]
        next_range = bars[i-1]

        new_range = None

        # start of next range in current range
        if next_range[0] >= current_range[0] and next_range[0] <= current_range[1]:

            if next_range[1] > current_range[1]:
                new_range = (current_range[0], next_range[1])
            else:
                new_range = current_range

        # end of next range in current range
        elif next_range[1] >= current_range[0] and next_range[1] <= current_range[1]:

            if next_range[0] < current_range[0]:
                new_range = (next_range[0], current_range[1])
            else:
                new_range = current_range

        if new_range is not None:
            bars.pop()
            bars.pop()
            bars.append(new_range)
        else:
            final_bars.append(bars.pop())

        i -= 1
    
    final_bars.append(bars.pop())

    return final_bars


if __name__ == "__main__":


    bars = [(1, 2), (5, 6), (3, 5), (7, 10), (2, 4)]
    print(fix_bars(bars))