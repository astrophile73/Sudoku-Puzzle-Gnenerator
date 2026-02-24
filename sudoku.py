import random
import time
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

SOLVER_NODE_LIMITS = {
    6: {
        "Easy": None,
        "Medium": None,
        "Hard": None,
        "Expert": None,
    },
    9: {
        "Easy": None,
        "Medium": 20000,
        "Hard": 12000,
        "Expert": 7000,
    },
    16: {
        "Easy": 18000,
        "Medium": 12000,
        "Hard": 7000,
        "Expert": 4500,
    },
}

PUZZLE_TIME_LIMITS_SEC = {
    6: {
        "Easy": None,
        "Medium": None,
        "Hard": None,
        "Expert": None,
    },
    9: {
        "Easy": None,
        "Medium": 1.2,
        "Hard": 1.4,
        "Expert": 1.8,
    },
    16: {
        "Easy": 0.8,
        "Medium": 1.0,
        "Hard": 1.2,
        "Expert": 1.5,
    },
}

MAX_GENERATION_TRIES = {
    6: {
        "Easy": 35,
        "Medium": 35,
        "Hard": 35,
        "Expert": 35,
    },
    9: {
        "Easy": 35,
        "Medium": 35,
        "Hard": 35,
        "Expert": 35,
    },
    16: {
        "Easy": 35,
        "Medium": 35,
        "Hard": 35,
        "Expert": 35,
    },
}


class SearchBudgetExceeded(Exception):
    pass


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


def _count_solutions(
    grid,
    spec,
    row_mask,
    col_mask,
    box_mask,
    full_mask,
    limit,
    node_limit=None,
    node_counter=None,
):
    if node_limit is not None:
        node_counter[0] += 1
        if node_counter[0] > node_limit:
            raise SearchBudgetExceeded

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
        count += _count_solutions(
            grid,
            spec,
            row_mask,
            col_mask,
            box_mask,
            full_mask,
            limit,
            node_limit=node_limit,
            node_counter=node_counter,
        )
        row_mask[r] ^= bit
        col_mask[c] ^= bit
        box_mask[_box_index(r, c, spec)] ^= bit
        grid[r][c] = 0
        if count >= limit:
            return count
    return count


def count_solutions(grid, spec, limit=2, node_limit=None):
    row_mask, col_mask, box_mask = _init_masks(grid, spec)
    full_mask = (1 << spec.size) - 1
    node_counter = [0]
    try:
        return _count_solutions(
            grid,
            spec,
            row_mask,
            col_mask,
            box_mask,
            full_mask,
            limit,
            node_limit=node_limit,
            node_counter=node_counter,
        )
    except SearchBudgetExceeded:
        return None


def _count_clues(grid):
    return sum(1 for row in grid for val in row if val != 0)


def _remove_numbers(puzzle, spec, target_clues, rng, node_limit=None, deadline_ts=None):
    size = spec.size
    positions = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(positions)
    clues = _count_clues(puzzle)
    budget_hits = 0
    timed_out = False
    for r, c in positions:
        if deadline_ts is not None and time.perf_counter() >= deadline_ts:
            timed_out = True
            break
        if clues <= target_clues:
            break
        if clues - 1 < target_clues:
            continue
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        sol_count = count_solutions(puzzle, spec, limit=2, node_limit=node_limit)
        if sol_count != 1:
            puzzle[r][c] = backup
            if sol_count is None:
                budget_hits += 1
        else:
            clues -= 1
    return puzzle, clues, budget_hits, timed_out


def generate_puzzle(
    spec,
    target_clues,
    rng,
    max_tries=35,
    node_limit=None,
    time_limit_sec=None,
):
    best = None
    best_diff = None
    for _ in range(max_tries):
        solution = _generate_full_solution(spec, rng)
        puzzle = [row[:] for row in solution]
        deadline_ts = None
        if time_limit_sec is not None:
            deadline_ts = time.perf_counter() + time_limit_sec
        puzzle, clues, budget_hits, timed_out = _remove_numbers(
            puzzle,
            spec,
            target_clues,
            rng,
            node_limit=node_limit,
            deadline_ts=deadline_ts,
        )
        diff = abs(clues - target_clues)
        meta = {
            "budget_hits": budget_hits,
            "timed_out": timed_out,
        }
        if diff == 0:
            return puzzle, solution, clues, True, meta
        if best is None or diff < best_diff:
            best = (puzzle, solution, clues, False, meta)
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
    node_limit = SOLVER_NODE_LIMITS[spec.size][difficulty]
    time_limit_sec = PUZZLE_TIME_LIMITS_SEC[spec.size][difficulty]
    max_tries = MAX_GENERATION_TRIES[spec.size][difficulty]
    puzzles = []
    solutions = []
    for idx in range(count):
        target = rng.randint(low, high)
        puzzle, solution, clues, exact, meta = generate_puzzle(
            spec,
            target,
            rng,
            max_tries=max_tries,
            node_limit=node_limit,
            time_limit_sec=time_limit_sec,
        )
        puzzles.append(puzzle)
        solutions.append(solution)
        if not exact and warn_cb:
            reason = "clue-target drift"
            if meta["timed_out"] and meta["budget_hits"] > 0:
                reason = "time limit + solver budget"
            elif meta["timed_out"]:
                reason = "time limit"
            elif meta["budget_hits"] > 0:
                reason = "solver budget"
            warn_cb(idx + 1, target, clues, reason)
        if progress_cb:
            progress_cb(idx + 1, count)
    return puzzles, solutions
