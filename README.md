# Custom Fantasy Optimizer 
<table>
  <tr>
    <td>
    Customizable fantasy football lineup optimizer built with Python and linear programming in PuLP. Optimize DraftKings lineups with adjustable player locks, exclusions, stacking, and position controls for the highest projection under roster and salary constraints. 
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

### How It Works
1) Fetches player pool for Sunday Classic contests from DraftKings API
2) Fetches PPR projections from Sleeper API and matches to player
3) Lets you interactively adjust constraints (locks, exclusions, stacks, position limits)
4) Uses PuLP to maximize projected points under DraftKings salary and roster rules
5) Displays the optimized lineup via Streamlit UI

### Features
- Interactive sortable queue and lineup tables  
- Lock or exclude players from your lineup 
- Require at least 1 FLEX from a specified team 
- QB + RB/WR/TE stacks (same team or opposing)
- RB + DST stacks
- Specify position for FLEX slot
- Exclude players opposing your DST 
- Set limit of 1 RB per team
- Optimizes highest projected lineup with PuLP

### Media
<img style="width:80%; height:80%" alt="Screenshot (130)" src="https://github.com/user-attachments/assets/270d2278-bd2e-487a-870a-7b9c1ce481f4" />

<img style="width:80%; height:80%" alt="Screenshot (144)" src="https://github.com/user-attachments/assets/6f2d28ec-64a4-4d0c-a379-89dfdea84687" />

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
