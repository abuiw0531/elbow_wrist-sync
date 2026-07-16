import time
import csv

class DataRecorder:
    def __init__(self):
        self.data = []
        self.is_recording = False
        self.start_time = 0.0

    def start(self):
        self.data.clear()
        self.is_recording = True
        self.start_time = time.time()

    def stop(self, filename):
        self.is_recording = False
        if not self.data:
            return
            
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Time(s)', 'Wrist', 'Elbow', 'Aperture_Binary', 'Aperture_Raw', 'Target'])
            writer.writerows(self.data)

    def add_entry(self, data_list, target_label=None):
        if self.is_recording:
            current_time = time.time()
            relative_time = current_time - self.start_time
            # data_list: [wrist, elbow, ap_bin, ap_raw]
            entry = [relative_time] + list(data_list)
            if target_label is not None:
                entry.append(target_label)
            self.data.append(entry)
