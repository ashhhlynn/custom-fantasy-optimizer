# Custom Fantasy Optimizer 
<table>
  <tr>
    <td>
    Customizable fantasy football lineup optimizer built with Python and linear programming in PuLP. Optimize DraftKings with flexible player, stacking, team, and position controls for highest projected lineups under position and salary constraints. Updated weekly during NFL season for Sunday Classic contests. 
    </td>
  </tr>
</table> 

#### :link: <a href="https://custom-fantasy-optimizer.streamlit.app/">Website</a></b>

### Technologies
- Python 3.8+
- PuLP
- DraftKings API
- Sleeper API
- Pandas
- Streamlit

### Features
- Interactive sortable queue and lineup tables  
- Lock or exclude players from your lineup 
- Specify position for FLEX
- QB + RB/WR/TE stacking options
- RB/DST stacks
- Exclude players opposing your DST 
- Optimizes highest projected lineup with PuLP

### How It Works
1) Fetches player pool for Sunday Classic contests from DraftKings API
2) Fetches PPR projections from Sleeper API and matches to player
3) Lets you interactively adjust constraints (locks, exclusions, stacks)
4) Uses PuLP to maximize projected points under DraftKings salary and roster rules
5) Displays the optimized lineup through Streamlit UI

### Media
Coming Soon! 

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
