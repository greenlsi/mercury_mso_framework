# Mercury M&amp;S&amp;O Framework for Fog Computing

Mercury is a Modeling, Simulation, and Optimization (M&amp;S&amp;O) Framework that aims to facilitate the fine-grained dimensioning and operation tasks of fog computing infrastructures.

Mercury's networking model is inspired by the 5G standard. It gathers Software-Defined Network (SDN) functions, radio bandwidth sharing algorithms, and access points discovery processes inspired by the 5G New Radio (NR) standard. Optimization tools allow you to automatically redistribute Radio Access Points and Edge Data Centers to reduce the negative effects of hot spots in your scenario.

With Mercury, you can explore real-time aspects of fog computing, such as perceived latency or power consumption of the infrastructure. Besides, different visualization tools are also provided. All the output is gathered in Comma-Separated Values (CSV) files for further analysis.

The code is fully written in Python 3, enabling you to override pre-defined models using your favorite Python packages (NumPy, pandas, TensorFlow, etc.). Mercury is built on top of [xDEVS](https://github.com/jlrisco/xdevs), a DEVS-compliant simulator.

# Requirements
- Python 3.5 or greater
- All the Python packages listed on the `requirements.txt` file
- The simulator has been tested on Linux and MacOS machines. Compatibility with Windows is not granted

# How to Get Mercury Up and Running?

- Clone this repository in your PC: `git clone https://github.com/greenlsi/mercury_mso_framework.git`
- Once cloned, move to the M&amp;S&amp;O framework folder: `cd mercury_mso_framework`
- Install all the required Python packages: `pip install -r requirements.txt`
- Create a `results` folder. This folder will hold the simulation results of your trial
- Let's run the example!: type `python3 samples/sample_mercury.py` and let it simulate

You are more than welcome to read through the `sample_mercury.py` file and tune different parameters to see their effect on the simulation outcome.
If you have any question regarding this preliminary version of Mercury, feel free to [send an email](mailto:r.cardenas@upm.es) with your request.

# Mercury Tutorial Examples

We are still working on this.

# References

We are still working on this.
