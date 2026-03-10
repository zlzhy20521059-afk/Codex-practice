import numpy as np
import os

class RCal:
    def __init__(self, directory):
        self.directory = directory
        self.data = None

    def read_data(self, filename):
        file_path = os.path.join(self.directory, filename)
        try:
            self.data = np.loadtxt(file_path)
            print(f"Data from {filename} read successfully.")
        except Exception as e:
            print(f"Error reading data: {e}")

    def output_results(self):
        if self.data is not None:
            mean = np.mean(self.data)
            std_dev = np.std(self.data)
            print(f"Mean: {mean}, Standard Deviation: {std_dev}")
        else:
            print("No data available to output results.")

# Example usage:
# rcal = RCal('/path/to/directory')
# rcal.read_data('data.txt')
# rcal.output_results()