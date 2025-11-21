"""
Core game logic for Minesweeper.

This module contains pure domain logic without any pygame or pixel-level
concerns. It defines:
- CellState: the state of a single cell
- Cell: a cell positioned by (col,row) with an attached CellState
- Board: grid management, mine placement, adjacency computation, reveal/flag

The Board exposes imperative methods that the presentation layer (run.py)
can call in response to user inputs, and does not know anything about
rendering, timing, or input devices.
"""

import random
from collections import deque
from typing import List, Tuple


class CellState:
    """Mutable state of a single cell.

    Attributes:
        is_mine: Whether this cell contains a mine.
        is_revealed: Whether the cell has been revealed to the player.
        is_flagged: Whether the player flagged this cell as a mine.
        adjacent: Number of adjacent mines in the 8 neighboring cells.
    """

    def __init__(self, is_mine: bool = False, is_revealed: bool = False, is_flagged: bool = False, adjacent: int = 0):
        self.is_mine = is_mine
        self.is_revealed = is_revealed
        self.is_flagged = is_flagged
        self.adjacent = adjacent


class Cell:
    """Logical cell positioned on the board by column and row."""

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row
        self.state = CellState()


class Board:
    """Minesweeper board state and rules.

    Responsibilities:
    - Generate and place mines with first-click safety
    - Compute adjacency counts for every cell
    - Reveal cells (iterative flood fill when adjacent == 0)
    - Toggle flags, check win/lose conditions
    """

    def __init__(self, cols: int, rows: int, mines: int):
        self.cols = cols
        self.rows = rows
        self.num_mines = mines
        self.cells: List[Cell] = [Cell(c, r) for r in range(rows) for c in range(cols)]
        self._mines_placed = False
        self.revealed_count = 0
        self.game_over = False
        self.win = False

    def index(self, col: int, row: int) -> int:
        """Return the flat list index for (col,row)."""
        return row * self.cols + col

    def is_inbounds(self, col: int, row: int) -> bool:
        """Return True if (col,row) is inside the board bounds."""
        return 0 <= col < self.cols and 0 <= row < self.rows

    def neighbors(self, col: int, row: int) -> List[Tuple[int, int]]:
        """Return list of valid neighboring coordinates around (col,row)."""
        deltas = [
            (-1, -1), (0, -1), (1, -1),
            (-1, 0),            (1, 0),
            (-1, 1),  (0, 1),  (1, 1),
        ]
        result = []
        for dc, dr in deltas:
            nc, nr = col + dc, row + dr
            if self.is_inbounds(nc, nr):
                result.append((nc, nr))
        return result

    def place_mines(self, safe_col: int, safe_row: int) -> None:
        """첫 클릭 위치와 그 주변을 안전하게 보장하며 지뢰를 랜덤 배치."""
        # 보드의 모든 좌표 생성
        all_positions = [(c, r) for r in range(self.rows) for c in range(self.cols)]

        # 안전 영역 정의: 첫 클릭 위치 + 인접 셀들
        forbidden = {(safe_col, safe_row)} | set(self.neighbors(safe_col, safe_row))

        # 지뢰 배치 가능한 위치 (안전 영역 제외)
        pool = [p for p in all_positions if p not in forbidden]

        # 섞어서 지뢰 배치할 위치 선택
        random.shuffle(pool)
        mine_positions = pool[:self.num_mines]

        # 지뢰 배치
        for col, row in mine_positions:
            idx = self.index(col, row)
            self.cells[idx].state.is_mine = True

        # 모든 셀의 인접 지뢰 개수 계산
        for r in range(self.rows):
            for c in range(self.cols):
                idx = self.index(c, r)
                if not self.cells[idx].state.is_mine:
                    # 주변 지뢰 개수 세기
                    adjacent_mines = 0
                    for nc, nr in self.neighbors(c, r):
                        neighbor_idx = self.index(nc, nr)
                        if self.cells[neighbor_idx].state.is_mine:
                            adjacent_mines += 1
                    self.cells[idx].state.adjacent = adjacent_mines

        self._mines_placed = True

    def reveal(self, col: int, row: int) -> None:
        """셀을 오픈하고, 인접 지뢰가 0개면 주변 셀을 반복적으로 오픈."""
        # 범위 체크
        if not self.is_inbounds(col, row):
            return

        # 첫 클릭이면 지뢰 배치
        if not self._mines_placed:
            self.place_mines(col, row)

        # 해당 셀의 상태 가져오기
        cell = self.cells[self.index(col, row)]

        # 이미 열렸거나 플래그가 있으면 무시
        if cell.state.is_revealed or cell.state.is_flagged:
            return

        # 지뢰를 밟은 경우
        if cell.state.is_mine:
            self.game_over = True
            self._reveal_all_mines()
            return

        # BFS로 flood fill 수행
        queue = deque([(col, row)])
        visited = set()

        while queue:
            c, r = queue.popleft()

            # 이미 방문했으면 스킵
            if (c, r) in visited:
                continue
            visited.add((c, r))

            idx = self.index(c, r)
            current_cell = self.cells[idx]

            # 이미 열렸거나 플래그가 있으면 스킵
            if current_cell.state.is_revealed or current_cell.state.is_flagged:
                continue

            # 지뢰면 스킵
            if current_cell.state.is_mine:
                continue

            # 셀 오픈
            current_cell.state.is_revealed = True
            self.revealed_count += 1

            # 인접 지뢰가 0개면 주변 셀들을 큐에 추가
            if current_cell.state.adjacent == 0:
                for nc, nr in self.neighbors(c, r):
                    if (nc, nr) not in visited:
                        queue.append((nc, nr))

        # 승리 조건 확인
        self._check_win()

    def toggle_flag(self, col: int, row: int) -> None:
        # TODO: Toggle a flag on a non-revealed cell.
        # if not self.is_inbounds(col, row):
        #     return
        
        pass

    def flagged_count(self) -> int:
        # TODO: Return current number of flagged cells.
        pass

    def _reveal_all_mines(self) -> None:
        """Reveal all mines; called on game over."""
        for cell in self.cells:
            if cell.state.is_mine:
                cell.state.is_revealed = True

    def _check_win(self) -> None:
        """Set win=True when all non-mine cells have been revealed."""
        total_cells = self.cols * self.rows
        if self.revealed_count == total_cells - self.num_mines and not self.game_over:
            self.win = True
            for cell in self.cells:
                if not cell.state.is_revealed and not cell.state.is_mine:
                    cell.state.is_revealed = True
