# SpikeSync

**SpikeSync** is a GUI tool that aligns neural spike data with video recordings, providing features like audio sonification, real-time signal visualization, and CSV export for further analysis.
![2025-05-02 20-48-41](https://github.com/user-attachments/assets/b28028bc-1397-46b4-9ca3-3e84fe7ed5e1)

## 1. Installation & Usage

### Prerequisites:
Ensure Python 3.6+ is installed:
```bash
python --version
```

### Installation Steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/SpikeSync.git
   cd SpikeSync
   ```

2. Set up a virtual environment:

   * **Windows**:

     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   * **macOS/Linux**:

     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Verify installation:

   ```bash
   pip list
   ```

### Running the Application:

1. Activate the virtual environment (if not already activated):

   * **Windows**:

     ```bash
     .\venv\Scripts\activate
     ```
   * **macOS/Linux**:

     ```bash
     source venv/bin/activate
     ```

2. Launch the application:

   ```bash
   python app.py
   ```
### Using SpikeSync

1. Upload the timestamp .dat file (trodes format)
2. Upload the raw data .dat file (trodes format)
3. Upload video file (.mp4) --> Should be "same" length as timestamp/raw files to accomodate drift
4. Input a start time / end time for the uploaded video (HH:MM:SS)
5. Click 'Align and Export'

6. (Optional) - Segment Info
   - Provides various information related to the cut chunk of video
![image](https://github.com/user-attachments/assets/98a34b31-6e8e-415d-861c-612df4981969)

7. (Optional) - Save Aligned CSV
   - Clicking this button provides the user with the data in the below format to further aid in analysis
     ```
     Time (clock rate) | Voltage (mV) | Frame | Second
     ```

For more information, refer to the full documentation or check the usage section within the GUI.
