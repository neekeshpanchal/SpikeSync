Here is the README formatted in markdown with both installation steps and usage condensed into one module:


# SpikeSync

**SpikeSync** is a GUI tool that aligns neural spike data with video recordings, providing features like audio sonification, real-time signal visualization, and CSV export for further analysis.

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

### Key Features:

* **Upload Data**: Import timestamp and raw data files.
* **Align Data**: Synchronize neural data with video.
* **Playback & Visualization**: Preview the video and visualize neural signals in real-time.
* **Export Data**: Save aligned data to CSV.

For more information, refer to the full documentation or check the usage section within the GUI.

```
```
