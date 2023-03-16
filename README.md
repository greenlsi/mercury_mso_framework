# Mercury M&amp;S&amp;O Framework for Fog Computing

Mercury is a Modeling, Simulation, and Optimization (M&amp;S&amp;O) Framework that aims to facilitate the fine-grained dimensioning and operation tasks of fog computing infrastructures.

Mercury's networking model is inspired by the 5G standard. It gathers Software-Defined Network (SDN) functions, radio bandwidth sharing algorithms, and access points discovery processes inspired by the 5G New Radio (NR) standard. Optimization tools allow you to automatically redistribute Radio Access Points and Edge Data Centers to reduce the negative effects of hot spots in your scenario.

With Mercury, you can explore real-time aspects of fog computing, such as perceived latency or power consumption of the infrastructure. Besides, different visualization tools are also provided. All the output is gathered in Comma-Separated Values (CSV) files or in a MySQL database for further analysis.

The code is fully written in Python 3, enabling you to override pre-defined models using your favorite Python packages (NumPy, pandas, TensorFlow, etc.). Mercury is built on top of [xDEVS](https://github.com/jlrisco/xdevs), a DEVS-compliant simulator.

# Requirements
- Python 3.6 or greater
- All the Python packages listed on the `requirements.txt` file
- The simulator has been tested on Linux and MacOS machines. Compatibility with Windows is not granted

# How to Get Mercury Up and Running?

- Clone this repository in your PC: `git clone https://github.com/greenlsi/mercury_mso_framework.git`
- Once cloned, move to the M&amp;S&amp;O framework folder: `cd mercury_mso_framework`
- Install all the required Python packages: `python3 `
- Install Mercury with all the required Python packages: `python3 setup.py install`
- Move to the SummerSim '20 example directory: `cd samples/summersim-2020`
- Create the folder that will hold the simulation results of your trial: `mkdir results`
- Let's run the example!: type `python3 main.py` and let it simulate

You are more than welcome to read through the `main.py` file and tune different parameters to see their effect on the simulation outcome.
If you have any question regarding this preliminary version of Mercury, feel free to [send an email](mailto:r.cardenas@upm.es) with your request.

# Mercury Tutorial Examples

We are still working on this.

# References

1. Román Cárdenas, Patricia Arroba, Roberto Blanco, Pedro Malagón, José L. Risco-Martín, and José M. Moya, [Mercury: A modeling, simulation, and optimization framework for data stream-oriented IoT applications](https://doi.org/10.1016/j.simpat.2019.102037), Simulation Modelling Practice and Theory, Volume 101, Pages: 102037, ISSN: 1569-190X, Elsevier, May 2020
2. Román Cárdenas, Patricia Arroba, José L. Risco-Martín, and José M. Moya, [Modeling and simulation of smart grid-aware edge computing federations](https://doi.org/10.1007/s10586-022-03797-8), Cluster Computing, Volume 26, Pages: 719–743, Springer Nature, February 2023
3. Román Cárdenas, Patricia Arroba, and José L. Risco-Martín, [Bringing AI to the edge: A formal M&amp;S specification to deploy effective IoT architectures](https://doi.org/10.1080/17477778.2020.1863755), Journal of Simulation, Volume 16:5, Pages: 494-511, Taylor and Francis, 2022
4. Román Cárdenas, Patricia Arroba, José M. Moya, and José L. Risco-Martín, [Multi-faceted modeling in the analysis and optimization of IoT complex systems](https://dl.acm.org/doi/abs/10.5555/3427510.3427537), Proceedings of the 2020 Summer Simulation Conference, Article No. 26, Pages: 1-12, SCS, July 2020
5. Román Cárdenas, Patricia Arroba, José M. Moya, and José L. Risco-Martín, [Edge Federation Simulator for Data Stream Analytics](https://dl.acm.org/doi/abs/10.5555/3374138.3374181), Proceedings of the 2019 Summer Simulation Conference, Article No. 43, Pages: 1-12, SCS, July 2019
