from flask import Flask, render_template, request, jsonify
import copy
from SudokuCSP import SudokuCSP, BruteForceSudoku

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        puzzle = request.json['puzzle']
        knights_rule = request.json['knights']
        
        # Convert input data into 9x9 grid
        grid = [[int(num) if num != '' else 0 for num in row] for row in puzzle]
        
        # Solve using SudokuCSP
        csp_solver = SudokuCSP(copy.deepcopy(grid), knights=knights_rule)
        csp_solution = csp_solver.solve()
        csp_moves =  csp_solver.get_moves()
        
        # Solve using Brute Force
        brute_solver = BruteForceSudoku(copy.deepcopy(grid), knights=knights_rule)
        brute_solution = brute_solver.solve()
        brute_moves =  brute_solver.get_moves()

        return jsonify({
            'csp_solved': csp_solution,
            'csp_grid': csp_solver.board if csp_solution else None,
            'csp_moves': csp_moves,
            'brute_solved': brute_solution,
            'brute_grid': brute_solver.board if brute_solution else None,
            'brute_moves': brute_moves
        })

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
