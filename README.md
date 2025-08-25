# Custom Fantasy Optimizer 
<table>
  <tr>
    <td>
    Customizable fantasy football lineup optimizer built with Python and linear programming in PuLP. Optimize DraftKings with flexible stacking, player, team, and position controls for highest projected lineups under position and salary constraints. Updated weekly during NFL season for Sunday Classic contests. 
    </td>
  </tr>
</table> 

#### :link: <a href="https://custom-fantasy-optimizer.streamlit.app/">Website</a>

### Technologies Used
- Python 3.8+
- PuLP
- DraftKings API
- Sleeper API
- Pandas
- Streamlit

### Features
- Interactive player queue and lineup tables with Streamlit 
- Lock or exclude players from lineup 
- Specify position for FLEX
- QB + RB/WR/TE stacking options
- RB/DST stacks
- Exclude players opposing DST 
- Optimize highest projected lineup with PuLP

### How It Works
1) Fetches contest player pool from DraftKings API
2) Fetches player projections from Sleeper API
3) Uses PuLP to optimize highest projected lineups under position/salary constraints
4) Lets you interactively adjust constraints (locks, exclusions, stacks)
5) Displays optimized lineup on Streamlit

### Media

### Setup 
   ```sh
   $ git clone https://github.com/ashhhlynn/custom-fantasy-optimizer.git
   ```
   ```sh
   $ cd custom-fantasy-optimizer
   ```
   ```sh
   $ pip install -r requirements.txt
   ```
   ```sh
   $ streamlit run dfs.py
   ```
### License 
This project is MIT licensed.
