import random
from dataclasses import dataclass


@dataclass(frozen=True)
class SudokuSpec:
    size: int
    block_rows: int
    block_cols: int


CLUE_RANGES = {
    6: {
        "Easy": (24, 28),
        "Medium": (20, 23),
        "Hard": (16, 19),
        "Expert": (12, 15),
    },
    9: {
        "Easy": (36, 45),
        "Medium": (30, 35),
        "Hard": (24, 29),
        "Expert": (17, 23),
    },
    16: {
        "Easy": (160, 190),
        "Medium": (130, 159),
        "Hard": (100, 129),
        "Expert": (80, 99),
    },
}


def spec_for_size(size):
    if size == 6:
        return SudokuSpec(size=6, block_rows=2, block_cols=3)
    if size == 9:
        return SudokuSpec(size=9, block_rows=3, block_cols=3)
    if size == 16:
        return SudokuSpec(size=16, block_rows=4, block_cols=4)
    raise ValueError("Unsupported puzzle size. Choose 6, 9, or 16.")


def _pattern(r, c, spec):
    return (
        spec.block_cols * (r % spec.block_rows) + r // spec.block_rows + c
    ) % spec.size


def _shuffle(rng, items):
    items = list(items)
    rng.shuffle(items)
    return items


def _generate_full_solution(spec, rng):
    size = spec.size
    digits = _shuffle(rng, range(1, size + 1))

    row_bands = _shuffle(rng, range(size // spec.block_rows))
    rows = [
        band * spec.block_rows + r
        for band in row_bands
        for r in _shuffle(rng, range(spec.block_rows))
    ]

    col_stacks = _shuffle(rng, range(size // spec.block_cols))
    cols = [
        stack * spec.block_cols + c
        for stack in col_stacks
        for c in _shuffle(rng, range(spec.block_cols))
    ]

    return [
        [digits[_pattern(r, c, spec)] for c in cols]
        for r in rows
    ]


def _box_index(r, c, spec):
    return (r // spec.block_rows) * (spec.size // spec.block_cols) + (
        c // spec.block_cols
    )


def _init_masks(grid, spec):
    size = spec.size
    row_mask = [0] * size
    col_mask = [0] * size
    box_mask = [0] * size
    for r in range(size):
        for c in range(size):
            val = grid[r][c]
            if val == 0:
                continue
            bit = 1 << (val - 1)
            row_mask[r] |= bit
            col_mask[c] |= bit
            box_mask[_box_index(r, c, spec)] |= bit
    return row_mask, col_mask, box_mask


def _select_cell(grid, spec, row_mask, col_mask, box_mask, full_mask):
    size = spec.size
    best = None
    best_count = size + 1
    for r in range(size):
        for c in range(size):
            if grid[r][c] != 0:
                continue
            mask = full_mask & ~(
                row_mask[r] | col_mask[c] | box_mask[_box_index(r, c, spec)]
            )
            count = mask.bit_count()
            if count == 0:
                return (r, c, 0)
            if count < best_count:
                best = (r, c, mask)
                best_count = count
                if count == 1:
                    return best
    return best


def _count_solutions(grid, spec, row_mask, col_mask, box_mask, full_mask, limit):
    choice = _select_cell(grid, spec, row_mask, col_mask, box_mask, full_mask)
    if choice is None:
        return 1
    r, c, mask = choice
    if mask == 0:
        return 0
    count = 0
    while mask:
        bit = mask & -mask
        mask -= bit
        val = bit.bit_length()
        grid[r][c] = val
        row_mask[r] |= bit
        col_mask[c] |= bit
        box_mask[_box_index(r, c, spec)] |= bit
        count += _count_solutions(grid, spec, row_mask, col_mask, box_mask, full_mask, limit)
        row_mask[r] ^= bit
        col_mask[c] ^= bit
        box_mask[_box_index(r, c, spec)] ^= bit
        grid[r][c] = 0
        if count >= limit:
            return count
    return count


def count_solutions(grid, spec, limit=2):
    row_mask, col_mask, box_mask = _init_masks(grid, spec)
    full_mask = (1 << spec.size) - 1
    return _count_solutions(grid, spec, row_mask, col_mask, box_mask, full_mask, limit)


def _count_clues(grid):
    return sum(1 for row in grid for val in row if val != 0)


def _remove_numbers(puzzle, spec, target_clues, rng):
    size = spec.size
    positions = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(positions)
    clues = _count_clues(puzzle)
    for r, c in positions:
        if clues <= target_clues:
            break
        if clues - 1 < target_clues:
            continue
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        if count_solutions(puzzle, spec, limit=2) != 1:
            puzzle[r][c] = backup
        else:
            clues -= 1
    return puzzle, clues


def generate_puzzle(spec, target_clues, rng, max_tries=35):
    best = None
    best_diff = None
    for _ in range(max_tries):
        solution = _generate_full_solution(spec, rng)
        puzzle = [row[:] for row in solution]
        puzzle, clues = _remove_numbers(puzzle, spec, target_clues, rng)
        diff = abs(clues - target_clues)
        if diff == 0:
            return puzzle, solution, clues, True
        if best is None or diff < best_diff:
            best = (puzzle, solution, clues, False)
            best_diff = diff
    return best


def generate_puzzles(count, spec, difficulty, rng=None, progress_cb=None, warn_cb=None):
    if rng is None:
        rng = random.Random()
    if spec.size not in CLUE_RANGES:
        raise ValueError("No clue ranges for this puzzle size.")
    if difficulty not in CLUE_RANGES[spec.size]:
        raise ValueError("Unsupported difficulty.")

    low, high = CLUE_RANGES[spec.size][difficulty]
    puzzles = []
    solutions = []
    for idx in range(count):
        target = rng.randint(low, high)
        puzzle, solution, clues, exact = generate_puzzle(spec, target, rng)
        puzzles.append(puzzle)
        solutions.append(solution)
        if not exact and warn_cb:
            warn_cb(idx + 1, target, clues)
        if progress_cb:
            progress_cb(idx + 1, count)
    return puzzles, solutions
