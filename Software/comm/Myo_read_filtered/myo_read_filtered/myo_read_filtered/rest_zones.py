import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# definitions : 
# rest zone = n (default = 10) consecutive points with value bellow "rest_thresh_val"

# extra print outs when in debug mode
DEBUG_MODE = False

# defining the amount of output sensors on the myo (for default values)
n_incoming_sensors = 8

# data fragments ment to fill the pipeline buffer
class DataCluster(): 

    def __init__(self, rz_detected, curr_mov_last=None, next_mov_first=None, whole_data=None):
        self.rest_zone_detected = rz_detected
        self.whole_data = whole_data
        self.curr_mov_last_seg = curr_mov_last
        self.next_mov_first_seg = next_mov_first

    def is_empty(self):
        return self.whole_data is None\
               and self.curr_mov_last_seg is None\
               and self.next_mov_first_seg is None

    def __str__(self):

        display_string = ""

        # rest zone detection flag
        if self.rest_zone_detected:
            display_string += "Rest zone detected\n\n"
        else: 
            display_string += "No rest zone detected\n\n"
        
        # getting data dimensions
        len_last_seg = 0
        len_first_seg = 0
        len_whole_data = 0
        if(self.curr_mov_last_seg is not None):
            len_last_seg = self.curr_mov_last_seg.shape[1]
        if(self.next_mov_first_seg is not None):
            len_first_seg = self.next_mov_first_seg.shape[1]
        if(self.whole_data is not None):
            len_whole_data = self.whole_data.shape[1]

        # display if the 2d data arrays
        display_string += "whole data (" + str(len_whole_data) + "): \n" + str(self.whole_data) + "\n"
        display_string += "curr_mov_last_seg (" + str(len_last_seg) +  "): \n" + str(self.curr_mov_last_seg) + "\n"
        display_string += "next_mov_first_seg (" + str(len_first_seg) + "): \n" + str(self.next_mov_first_seg) + "\n"

        return display_string



# debug function to display data points
def display_emg_points(data, n_emg=n_incoming_sensors, plot_title=None): 

    for i in range(n_emg): 
        x = np.arange(data.shape[1])
        cur_emg_points = data[i, : ]
        data_label = "emg " + str(i+1)
        plt.plot(x, cur_emg_points, linewidth=2, label=data_label)
    
    if(plot_title is not None):
        plt.title(plot_title)

    plt.show()



# cutting the rest zones out of the provided data
# input : X has to be a (n_incoming_sensors, n_entries) numpy nd_array, where n_entries < rms_buff_size
# input : "rest_thresh_val" defines the threshold rms value for restzones 
# returns a DataCluster instance
def segment_data(X, rms_buff_size=10, rest_thresh_val=5):

    # getting indicies of rest zones in the input
    rest_zone_indicies = get_restzone_indicies(X, rms_buff_size, rest_thresh_val)
    
    # no rest zones were detected 
    if(len(rest_zone_indicies) == 0):
        return DataCluster(rz_detected=False, whole_data=X)

    # getting the start and end indicies for all the rest zones
    rest_zone_ranges = get_restzone_ranges(rest_zone_indicies, rms_buff_size)

    # getting a data cluster from the input data
    segmented_data = generate_DataCluster(X, rest_zone_ranges)
    
    if(DEBUG_MODE): 
        display_emg_points(X, plot_title="Raw data from sensors")
        if(segmented_data.curr_mov_last_seg is not None): 
            display_emg_points(segmented_data.curr_mov_last_seg, plot_title="Last segment of current movement")
        if(segmented_data.next_mov_first_seg is not None):
            display_emg_points(segmented_data.next_mov_first_seg, plot_title="First segment of next movement")

    return segmented_data



# Scans the input data matrix "X" of shape (n_emgs, n_entries) with an rms buffer
# Returns : "rest_zone_indicies", the indicies at which rest zones end
def get_restzone_indicies(X, rms_buff_size, rest_thresh_val=5):

    n_emgs = X.shape[0]
    n_entries = X.shape[1]
    rms_buffer = np.empty((n_emgs, rms_buff_size))

    # data in X cant be smaller than the rms range
    if(rms_buff_size >= n_entries):
        raise ValueError('RMS buffer size must be smaller or equal to the amount of samples')

    # initial filling of the rms buffer
    for x in range(n_emgs): 
        for y in range(rms_buff_size): 
            rms_buffer[x][y] = X[x][y]

    # calculating the different rms values
    rest_zone_indicies = []
    buffer_steps = n_entries - rms_buff_size
    for step_i in range(buffer_steps):
        
        # calculating the rms values (one for each emg)
        rms_vals = []
        for emg_i in range(n_emgs): 
            temp_row = rms_buffer[emg_i, :]
            rms_vals.append(np.sqrt(np.mean(temp_row**2)))

        # changing the current buffer for next calculation
        buff_position = step_i % rms_buff_size
        for emg_i in range(n_emgs):
            rms_buffer[emg_i][buff_position] = X[emg_i][rms_buff_size + buff_position]
      
        # if current rms buffer configuration is a rest_zone, take note of it
        rest_zone_detected = True
        for i in range(n_emgs):
            if(rms_vals[i] > rest_thresh_val):
                rest_zone_detected = False
                break

        if(rest_zone_detected): 
            rest_zone_indicies.append(step_i + rms_buff_size)

        if(DEBUG_MODE):
            print("rms vals #", step_i, " : ", rms_vals, "\n")

    return rest_zone_indicies



# input : "rest_zone_indicies" = ending indicies of restzones in the input data
# combines continuous rest zones to make bigger ones
# notes the start and finish index for all the restzones 
# returns : "rest_zone_ranges" = [[start index, finish index], [], [] ...] one element per restzone
def get_restzone_ranges(rest_zone_indicies, rms_buff_size):

    # container for the index range of rest zones
    rest_zone_ranges = []

    # single rest zone was detected 
    if(len(rest_zone_indicies) == 1):
        rest_zone_ranges.append([rest_zone_indicies[0] - rms_buff_size, rest_zone_indicies[0]])

    # multiple rest zones were detected
    elif(len(rest_zone_indicies) > 1): 

        range_s = 0
        range_start = True

        for i in range(len(rest_zone_indicies)-1): 

            current_index = rest_zone_indicies[i]
            next_index = rest_zone_indicies[i+1]

            # starting a new rest zone range
            if(range_start): 
                range_s = current_index - rms_buff_size
                range_start = False

            # continuity broke (end of current zone)
            if(current_index + 1 != next_index):
                range_start = True
                rest_zone_ranges.append([range_s, current_index])

            # end of the input buffer reached
            elif(i == len(rest_zone_indicies)-2):
                range_start = True
                rest_zone_ranges.append([range_s, next_index])

        if(DEBUG_MODE):
            print("\nrest zone indicies : \n", rest_zone_indicies)
            print("\nrest zone ranges : \n", rest_zone_ranges)

    return rest_zone_ranges



# Generates de a data cluster from the input data
# Data before de first restzone = "cur_mov_last_seg"
# Data after the last restzone = "next_mov_first_seg"
# input : X = input data of shape (n_incoming_sensors, n_entries)
# input : rest_zone_ranges = list of start and finish indicies for every rest zone in the data
# output : DataCluster for provided input
def generate_DataCluster(X, rest_zone_ranges):

    # cutting the last segment of the current mouvement
    if(rest_zone_ranges[0][0] != 0):
        cur_mov_last_seg = X[ : , 0 : rest_zone_ranges[0][0]]
    else: cur_mov_last_seg = None

    # cutting the first segment of the next mouvement 
    if(rest_zone_ranges[len(rest_zone_ranges)-1][1] != 49):
        next_mov_first_seg = X[ : , rest_zone_ranges[len(rest_zone_ranges)-1][1] : 49]
    else: next_mov_first_seg = None
    
    if(DEBUG_MODE):
        print("\ncur_mov_last_seg : \n", cur_mov_last_seg)
        print("\nnext_mov_first_seg : \n", next_mov_first_seg)

    # if start and end of the input data are rest zones, no data will be sent to the pipeline buffer
    return DataCluster(rz_detected=True, curr_mov_last=cur_mov_last_seg, 
                               next_mov_first=next_mov_first_seg)