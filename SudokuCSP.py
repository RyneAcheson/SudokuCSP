from collections import deque
import copy

# Solves sudoku grids as a CSP (constraint satisfaction problem)
# utilizing the AC-3 (Arc Consistency Algorithm #3) Algorithm in
# combination with backtracking, minimum remaining values (MRV) for
# variable ordering and least constraining value (LCV) for value ordering.
# The idea is that utilizing these heuristics and techniques will reduce
# the "moves" (defined as inserting a number) required to solve complex
# grids and thereby reducing the time required to solve the grid.
# Further detail is included in the report.
class SudokuCSP:
    
    # Initialize the board, the "knights" variable is a boolean that represents
    # if the user wants to add the additional constraint that identical numbers
    # cannot be seperated by a knight's move in chess (2x1 L shape away). This is
    # optional is by default not included.
    def __init__(self, board, knights=False):
        self.board = board
        self.knights = knights
        self.size = 9
        self.subgrid_size = int(self.size ** 0.5)

        # List containing all the possible ways a knight can move in chess
        # represented by (delta x, delta y)
        self.knight_moves = [
            (2, 1), (2, -1), (-2, 1), (-2, -1),
            (1, 2), (1, -2), (-1, 2), (-1, -2)
        ]

         # Dictionary mapping a coordinate to remaining values
        self.domains = {}

        # double ended queue that allows for elements to be accessed/inserted/popped from either side
        self.constraints = deque()

        # set up the domains for each cell (#s 1-9)
        self.initialize_domain()

        # set up the constraints graph where each constraint is a tuple between two coordinates 
        # (where is a coordinate is a tuple of (row, col)) indicating that they constrain each other
        self.initialize_constraints()

        # counter that serves as a metric to measure the efficiency of the CSP solver
        self.move_counter = 0
    
    # Initialzes the domains of each cell, if the cell is empty (0 in grid) then the domain of that cell
    # is initialized as a set containing the numbers 1-9 inclusive, otherwise if the cell already contains
    # a number then the domain is just that number
    def initialize_domain(self):
        for row in range(self.size):
            for col in range(self.size):
                if self.board[row][col] == 0:
                    self.domains[(row, col)] = set(range(1, 10))
                else:
                    self.domains[(row, col)] = {self.board[row][col]}

    # Creates a representation of a constraint graph using a double ended queue of tuples of 2 cells
    # representing that those two cells constrain each other. Calls the neighbors method which returns
    # a list of tuples (each tuple representing the coordinates of a neighboring cell) that can be "seen"
    # and is constrained by the current cell. If the cell is not empty then there is no need to initialize
    # the constraints
    def initialize_constraints(self):
        for row in range(self.size):
            for col in range(self.size):
                if self.board[row][col] == 0:
                    neighbors = self.neighbors((row, col))
                    for neighbor in neighbors:
                        self.constraints.append(((row, col), neighbor))

    # The AC-3 Algorithm uses Arc Consistency to prune the domains of each
    # cell as much as possible before selecting values from them. A pair of 
    # cells is arc consistent if for each value x in the domain of Cell1 there
    # exists an a value y in the domain of Cell2 s.t. that x and y satisfy the
    # constraints between Cell1 and Cell2.
    def ac3(self):
        # While constraints still exist
        while self.constraints:
            # pops a constraint tuple from the double ended queue
            cell1, cell2 = self.constraints.popleft()

            # updates the domain of cell1 if cell1 and cell2 are arc consistent
            updated = self.update_domain(cell1, cell2)

            # if they are arc consistent...
            if updated:
                # If there are no values left in the domain of cell1 then the grid is
                # impossible to solve.
                if not self.domains[cell1]:
                    return False
                
                # Adds new constraints between neighbors of cell1 and cell1
                for cell3 in self.neighbors(cell1):
                    if cell3 != cell2:
                        self.constraints.append((cell3, cell1))

        # returns true when all constraints have been accounted for and domains have been pruned
        return True

    # updates the domain of cell1 if cell1 and cell2 are arc consistent
    def update_domain(self, cell1, cell2):
        updated = False
        for x in set(self.domains[cell1]):
            if all(x == y for y in self.domains[cell2]):
                self.domains[cell1].remove(x)
                updated = True
        return updated
    
    # returns all the cells that the cell parameter can see. That is according
    # to row, column, box, and knight rules.
    def neighbors(self, cell):
        row, col = cell
        neighbors = set()

        for i in range(self.size):
            if i != col:
                neighbors.add((row, i))
            if i != row:
                neighbors.add((i, col))
                
        # Top left corner of the box the current cell is in
        box_start_row, box_start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                r, c = box_start_row + i, box_start_col + j
                if (r, c) != cell:
                    neighbors.add((r, c))
        
        if self.knights:
            for delta_row, delta_col in self.knight_moves:
                x, y = row + delta_row, col + delta_col
                if 0 <= x < self.size and 0 <= y < self.size:
                    neighbors.add((x, y))

        return neighbors

    # After the domains have been pruned through the AC-3 algorithm we will attempt
    # to solve the grid.
    def solve(self):

        # If the grid is impossible to solve...
        if not self.ac3():
            return False
        
        return self.backtrack()
    
    def backtrack(self):
        # Looks for an empty cell with the Minimum Remaining Values left in its
        # domain (this is the MRV heuristic)
        empty = self.mrv()

        # If there are no more empty cells then the grid has been solved.
        if not empty:
            return True
        row, col = empty

        # lcv_list contains a list of the numbers in the cell's domain, sorted by the number
        # how constraining that number is on other cells. This is the LCV heuristic
        lcv_list = self.lcv(row, col)
        for num in lcv_list:
            if num in self.domains[(row, col)]:

                # Modifies the domain of the current cell and its neighbors, storing 
                # the original domain information of itself and its neighbors in "original_domains"
                # This will increase the move counter by 1 since a number has been placed in the grid.
                changes, original_domains = self.set_domain(row, col, num)

                # Recursively calls the solve method, if solvable returns True
                if self.solve():
                    return True
                
                # If not solvable then the original domains of the current cell and its neighbors
                # are restored and the next number will be checked for its validity.
                self.restore(row, col, changes, original_domains)

        # If none of the numbers result in a solvable grid then the grid is impossible to solve.
        return False

    # Returns the cell with the minimum remaining values, meaning it's domain has been pruned the most
    def mrv(self):
        min_cell = None
        min_values = self.size + 1
        for row in range(self.size):
            for col in range(self.size):
                if self.board[row][col] == 0 and len(self.domains[(row, col)]) < min_values:
                    min_cell = (row, col)
                    min_values = len(self.domains[(row, col)])
        return min_cell

    # Returns a list of values within a cell's domain sorted how constraining that value is on other cells
    def lcv(self, row, col):

        # Helper function that counts the number of conflicts a value has with neighboring cells.
        def num_conflicts(num):
            count = 0
            for (r, c) in self.neighbors((row, col)):
                if (r, c) in self.domains and num in self.domains[(r, c)]:
                    count += 1
            return count
        
        lcv_list = sorted(self.domains[(row, col)], key=num_conflicts)
        return lcv_list
    
    # Modifies the domain of the current cell and all of its neighbors, removing num.
    # Will also return the original domains so they can be restored if the grid is not
    # solvable with num in the current cell.
    def set_domain(self, row, col, num):
        self.board[row][col] = num
        changes = []
        original_domains = {}

        original_domains[(row, col)] = self.domains[(row, col)].copy()

        for (r, c) in self.neighbors((row, col)):
            if num in self.domains[(r, c)]:
                if (r, c) not in original_domains:
                    original_domains[(r, c)] = self.domains[(r, c)].copy()
                self.domains[(r, c)].remove(num)
                changes.append((r, c))

        self.domains[(row, col)] = {num}
        self.move_counter += 1

        return changes, original_domains

    # Restores the domain of all cells affected by set_domain to the original domains
    def restore(self, row, col, changes, original_domains):
        self.board[row][col] = 0

        # Restore the previous domains of all affected cells
        for (r, c) in changes:
            self.domains[(r, c)] = original_domains[(r, c)]

        # Restore the domain of the current cell
        self.domains[(row, col)] = original_domains[(row, col)]

    # Prints the board and the number of moves required
    def print_board(self):
        for row in self.board:
            print(" ".join(str(num) if num != 0 else '.' for num in row))
        print(f"Total moves made: {self.move_counter}") 

    def get_moves(self):
        return self.move_counter


# This class represents a brute force approach towards solving a sudoku problem,
# which is obviously much less efficient but serves as a good benchmark and comparison
# for the approach utilizing the AC-3 algorithm along with the MRV and LCV heuristics.
class BruteForceSudoku:

    # Initialize the board, including an option for knight moves
    def __init__(self, board, knights = False):
        self.board = board
        self.size = 9
        self.move_counter = 0
        self.knights = knights
        self.knight_moves = [
            (2, 1), (2, -1), (-2, 1), (-2, -1),
            (1, 2), (1, -2), (-1, 2), (-1, -2)
        ]
        
    # Method that solves the sudoku grid with a brute force approach, trying every number
    # 1-9 and then checking if that number works. 
    def solve(self):

        # Finds the first empty cell in the grid, if there are no more empty cells left
        # the grid has been solved
        empty = self.find_empty()
        if not empty:
            return True
        row, col = empty

        # Tries every number 1-9 and checks if it is a valid placement, if that number is
        # then it will be inserted into the grid and solve will be recursively called.
        # If when solve is recursively called, the board becomes impossible to solve then
        # the cell will be reset to 0 (indicating empty) and the next number in the 1-9
        # sequence will be tried. Every valid placement (even if it doesn't result in a solved
        # grid) will increment the move counter by 1.
        for num in range(1, 10):
            if self.is_valid(num, row, col):
                self.board[row][col] = num
                self.move_counter += 1
                if self.solve():
                    return True
                self.board[row][col] = 0

        return False

    # Method that finds the first empty cell in the grid
    def find_empty(self):
        for row in range(self.size):
            for col in range(self.size):
                if self.board[row][col] == 0:
                    return (row, col)
        return None

    # Checks if the number placed in the cell (at the row and col coordinates passed in)
    # is a valid placement according to the row, column, box, and knight constraints
    def is_valid(self, num, row, col):
        for i in range(self.size):
            if self.board[row][i] == num:
                return False

        for i in range(self.size):
            if self.board[i][col] == num:
                return False

        # Top left corner of the box the current cell is in
        box_start_row, box_start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                r, c = box_start_row + i, box_start_col + j
                if self.board[r][c] == num:
                    return False
        
        # only checks knight constraints if knight rules are active
        if self.knights:
            for delta_row, delta_col in self.knight_moves:
                r, c = row + delta_row, col + delta_col
                if 0 <= r < self.size and 0 <= c < self.size:
                    if self.board[r][c] == num:
                        return False
        return True

    # Prints the board
    def print_board(self):
        for row in self.board:
            print(" ".join(str(num) if num != 0 else '.' for num in row))
        print(f"Total moves made: {self.move_counter}")

    def get_moves(self):
        return self.move_counter


if __name__ == "__main__":
    sudoku_board = [
        [5, 0, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]
    nyt_easy = [
        [4, 1, 5, 8, 3, 0, 0, 9, 0],
        [0, 0, 3, 0, 0, 9, 1, 0, 4],
        [0, 0, 2, 1, 5, 0, 0, 0, 6],
        [9, 0, 0, 7, 8, 3, 0, 0, 0],
        [2, 0, 0, 0, 0, 0, 3, 8, 1],
        [5, 0, 0, 0, 1, 2, 4, 0, 0],
        [0, 0, 4, 9, 0, 0, 0, 6, 3],
        [3, 8, 0, 5, 0, 0, 0, 4, 0],
        [0, 0, 9, 3, 0, 7, 5, 0, 0]
    ]

    nyt_medium = [
        [5, 0, 0, 0, 0, 0, 3, 0, 0],
        [0, 0, 9, 0, 0, 0, 0, 2, 7],
        [4, 0, 0, 1, 0, 5, 0, 0, 9],
        [2, 0, 0, 0, 0, 0, 0, 7, 0],
        [0, 0, 0, 0, 0, 6, 0, 0, 0],
        [0, 0, 6, 0, 4, 9, 0, 0, 0],
        [3, 0, 0, 0, 2, 7, 9, 0, 0],
        [0, 8, 0, 6, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 3, 4, 0, 1, 2]
    ]

    nyt_hard = [
        [0, 0, 0, 0, 3, 0, 4, 0, 0],
        [9, 0, 0, 4, 0, 0, 3, 0, 0],
        [3, 0, 0, 0, 0, 0, 0, 7, 2],
        [0, 0, 9, 0, 0, 5, 0, 0, 0],
        [8, 0, 0, 0, 1, 0, 0, 0, 0],
        [7, 0, 0, 6, 0, 0, 5, 2, 9],
        [0, 0, 0, 1, 0, 0, 7, 0, 0],
        [6, 0, 1, 0, 5, 0, 0, 0, 8],
        [0, 4, 0, 0, 0, 0, 0, 1, 0]
    ]

    knight1 = [
        [7, 0, 0, 2, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 6, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 3, 0, 0, 0, 0, 0, 8, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [9, 5, 0, 0, 0, 0, 0, 4, 3],
        [3, 0, 0, 0, 0, 0, 0, 9, 8],
        [0, 0, 1, 0, 0, 0, 2, 0, 0],
        [5, 0, 0, 7, 0, 8, 0, 0, 4]
    ]
    hardest1 = [
        [0, 0, 5, 3, 0, 0, 0, 0, 0],
        [8, 0, 0, 0, 0, 0, 0, 2, 0],
        [0, 7, 0, 0, 1, 0, 5, 0, 0],
        [4, 0, 0, 0, 0, 5, 3, 0, 0],
        [0, 1, 0, 0, 7, 0, 0, 0, 6],
        [0, 0, 3, 2, 0, 0, 0, 8, 0],
        [0, 6, 0, 5, 0, 0, 0, 0, 9],
        [0, 0, 4, 0, 0, 0, 0, 3, 0],
        [0, 0, 0, 0, 0, 9, 7, 0, 0],
    ]

    CSP_grid = copy.deepcopy(knight1)
    CSP_solver = SudokuCSP(CSP_grid, knights = True)
    if CSP_solver.solve():
        print("Sudoku solved:")
        CSP_solver.print_board()
    else:
        print("No solution exists")

    brute_grid = copy.deepcopy(knight1)
    brute_solver = BruteForceSudoku(brute_grid, knights = True)
    if brute_solver.solve():
        print("Sudoku solved:")
        brute_solver.print_board()
    else:
        print("No solution exists")
