import json
from collections import deque

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Building, GameSession, Piece, Tile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TERRAIN_MOVE_COST = {
    'plains': 1,
    'road': 0.5,
    'forest': 2,
    'mountain': 3,
    'water': 4,
}

TERRAIN_DEF_BONUS = {
    'plains': 0,
    'road': 0,
    'forest': 3,
    'mountain': 5,
    'water': -2,
}

WATER_BLOCKED = {'pawn', 'bishop', 'rook', 'queen', 'king'}
BOARD_SIZE = 8


# ---------------------------------------------------------------------------
# Board setup
# ---------------------------------------------------------------------------

def _make_piece(game, piece_type, owner, x, y):
    stats = Piece.STATS[piece_type]
    return Piece(
        game=game, type=piece_type, owner=owner, x=x, y=y,
        hp=stats['hp'], max_hp=stats['hp'],
        attack=stats['attack'], defense=stats['defense'],
        move_points=stats['move_points'],
    )


def _setup_board(game):
    terrain_overrides = {
        (2, 2): 'forest', (2, 5): 'forest',
        (3, 3): 'forest', (5, 3): 'forest',
        (5, 2): 'mountain', (5, 5): 'mountain',
        (4, 3): 'mountain', (4, 4): 'mountain',
        (1, 4): 'road', (2, 4): 'road', (3, 4): 'road',
        (4, 4): 'road', (5, 4): 'road', (6, 4): 'road',
    }

    tiles_to_create = []
    for x in range(BOARD_SIZE):
        for y in range(BOARD_SIZE):
            terrain = terrain_overrides.get((x, y), 'plains')
            tiles_to_create.append(Tile(game=game, x=x, y=y, terrain_type=terrain))
    Tile.objects.bulk_create(tiles_to_create)

    tile_map = {(t.x, t.y): t for t in game.tiles.all()}

    b1 = Building.objects.create(game=game, type='castle', owner=1)
    b2 = Building.objects.create(game=game, type='castle', owner=2)
    h1 = Building.objects.create(game=game, type='house', owner=None)
    h2 = Building.objects.create(game=game, type='house', owner=None)
    h3 = Building.objects.create(game=game, type='house', owner=None)
    h4 = Building.objects.create(game=game, type='house', owner=None)

    tile_map[(0, 3)].building = b1
    tile_map[(7, 4)].building = b2
    tile_map[(3, 2)].building = h1
    tile_map[(3, 5)].building = h2
    tile_map[(4, 2)].building = h3
    tile_map[(4, 5)].building = h4

    Tile.objects.bulk_update(
        [tile_map[(0, 3)], tile_map[(7, 4)],
         tile_map[(3, 2)], tile_map[(3, 5)],
         tile_map[(4, 2)], tile_map[(4, 5)]],
        ['building']
    )

    back_row = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
    pieces = []
    for col, ptype in enumerate(back_row):
        pieces.append(_make_piece(game, ptype, 1, 0, col))
    for col in range(BOARD_SIZE):
        pieces.append(_make_piece(game, 'pawn', 1, 1, col))
    for col, ptype in enumerate(back_row):
        pieces.append(_make_piece(game, ptype, 2, 7, col))
    for col in range(BOARD_SIZE):
        pieces.append(_make_piece(game, 'pawn', 2, 6, col))
    Piece.objects.bulk_create(pieces)


# ---------------------------------------------------------------------------
# Movement helpers
# ---------------------------------------------------------------------------

def _get_valid_moves(piece, all_pieces, tile_map):
    occupied = {(p.x, p.y): p.owner for p in all_pieces if p.pk != piece.pk}

    if piece.type == 'knight':
        return _knight_moves(piece, occupied)

    if piece.type == 'bishop':
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif piece.type == 'rook':
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    else:
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    visited = {(piece.x, piece.y): 0.0}
    queue = deque([(piece.x, piece.y, 0.0)])
    reachable = set()

    while queue:
        cx, cy, cost = queue.popleft()
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE):
                continue
            tile = tile_map.get((nx, ny))
            if tile is None:
                continue
            terrain = tile.terrain_type
            if terrain == 'water' and piece.type in WATER_BLOCKED:
                continue
            new_cost = cost + TERRAIN_MOVE_COST.get(terrain, 1)
            if new_cost > piece.move_points:
                continue
            occupant = occupied.get((nx, ny))
            if occupant == piece.owner:
                continue
            if new_cost < visited.get((nx, ny), float('inf')):
                visited[(nx, ny)] = new_cost
                reachable.add((nx, ny))
                if occupant is None:
                    queue.append((nx, ny, new_cost))

    return reachable


def _knight_moves(piece, occupied):
    jumps = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
    return {
        (piece.x + dx, piece.y + dy)
        for dx, dy in jumps
        if 0 <= piece.x + dx < BOARD_SIZE
        and 0 <= piece.y + dy < BOARD_SIZE
        and occupied.get((piece.x + dx, piece.y + dy)) != piece.owner
    }


def _get_valid_attacks(piece, all_pieces):
    enemy_pos = {(p.x, p.y) for p in all_pieces if p.owner != piece.owner}
    return {
        (piece.x + dx, piece.y + dy)
        for dx in [-1, 0, 1] for dy in [-1, 0, 1]
        if not (dx == 0 and dy == 0)
        and (piece.x + dx, piece.y + dy) in enemy_pos
    }


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize_state(game):
    tiles = list(game.tiles.select_related('building').all())
    pieces = list(game.pieces.all())
    buildings = list(game.buildings.all())

    return {
        'game_id': game.pk,
        'current_player': game.current_player,
        'turn_number': game.turn_number,
        'status': game.status,
        'winner': game.winner,
        'tiles': [
            {'x': t.x, 'y': t.y, 'terrain': t.terrain_type, 'building_id': t.building_id}
            for t in tiles
        ],
        'pieces': [
            {
                'id': p.pk, 'type': p.type, 'owner': p.owner,
                'x': p.x, 'y': p.y, 'hp': p.hp, 'max_hp': p.max_hp,
                'attack': p.attack, 'defense': p.defense,
                'move_points': p.move_points, 'xp': p.xp, 'level': p.level,
                'has_moved': p.has_moved, 'has_attacked': p.has_attacked,
            }
            for p in pieces
        ],
        'buildings': [
            {'id': b.pk, 'type': b.type, 'owner': b.owner, 'hp': b.hp}
            for b in buildings
        ],
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def new_game(request):
    game = GameSession.objects.create()
    _setup_board(game)
    return redirect('game_view', game_id=game.pk)


def game_view(request, game_id):
    get_object_or_404(GameSession, pk=game_id)
    return render(request, 'game/game.html', {'game_id': game_id})


def game_state(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id)
    return JsonResponse(_serialize_state(game))


def valid_moves(request, game_id, piece_id):
    game = get_object_or_404(GameSession, pk=game_id)
    piece = get_object_or_404(Piece, pk=piece_id, game=game)
    all_pieces = list(game.pieces.all())
    tile_map = {(t.x, t.y): t for t in game.tiles.all()}

    moves = list(_get_valid_moves(piece, all_pieces, tile_map)) if not piece.has_moved else []
    attacks = list(_get_valid_attacks(piece, all_pieces)) if not piece.has_attacked else []

    return JsonResponse({
        'moves': [{'x': x, 'y': y} for x, y in moves],
        'attacks': [{'x': x, 'y': y} for x, y in attacks],
    })


@require_POST
def move_piece(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id)
    if game.status != GameSession.STATUS_ACTIVE:
        return JsonResponse({'error': 'Game is over'}, status=400)

    try:
        data = json.loads(request.body)
        piece_id = data['piece_id']
        tx, ty = int(data['x']), int(data['y'])
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    piece = get_object_or_404(Piece, pk=piece_id, game=game)
    if piece.owner != game.current_player:
        return JsonResponse({'error': 'Not your piece'}, status=403)
    if piece.has_moved:
        return JsonResponse({'error': 'Already moved'}, status=400)

    all_pieces = list(game.pieces.all())
    tile_map = {(t.x, t.y): t for t in game.tiles.all()}

    if (tx, ty) not in _get_valid_moves(piece, all_pieces, tile_map):
        return JsonResponse({'error': 'Invalid move'}, status=400)

    if any(p.x == tx and p.y == ty and p.owner != piece.owner for p in all_pieces):
        return JsonResponse({'error': 'Tile occupied by enemy — use attack'}, status=400)

    piece.x, piece.y, piece.has_moved = tx, ty, True
    piece.save(update_fields=['x', 'y', 'has_moved'])
    return JsonResponse(_serialize_state(game))


@require_POST
def attack_piece(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id)
    if game.status != GameSession.STATUS_ACTIVE:
        return JsonResponse({'error': 'Game is over'}, status=400)

    try:
        data = json.loads(request.body)
        attacker_id = data['attacker_id']
        target_id = data['target_id']
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    attacker = get_object_or_404(Piece, pk=attacker_id, game=game)
    target = get_object_or_404(Piece, pk=target_id, game=game)

    if attacker.owner != game.current_player:
        return JsonResponse({'error': 'Not your piece'}, status=403)
    if target.owner == game.current_player:
        return JsonResponse({'error': 'Cannot attack own piece'}, status=400)
    if attacker.has_attacked:
        return JsonResponse({'error': 'Already attacked'}, status=400)
    if abs(attacker.x - target.x) > 1 or abs(attacker.y - target.y) > 1:
        return JsonResponse({'error': 'Not adjacent'}, status=400)

    tile_map = {(t.x, t.y): t for t in game.tiles.all()}
    defender_tile = tile_map.get((target.x, target.y))
    terrain_def = TERRAIN_DEF_BONUS.get(
        defender_tile.terrain_type if defender_tile else 'plains', 0
    )

    damage = max(1, attacker.attack - (target.defense + terrain_def))
    target.hp -= damage
    attacker.has_attacked = True
    attacker.has_moved = True
    attacker.xp += 10

    if target.hp <= 0:
        attacker.xp += 20
        attacker.save(update_fields=['has_attacked', 'has_moved', 'xp'])
        target_type = target.type
        target.delete()
        if target_type == 'king':
            game.status = GameSession.STATUS_FINISHED
            game.winner = game.current_player
            game.save(update_fields=['status', 'winner'])
    else:
        target.save(update_fields=['hp'])
        attacker.save(update_fields=['has_attacked', 'has_moved', 'xp'])

    return JsonResponse(_serialize_state(game))


@require_POST
def end_turn(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id)
    if game.status != GameSession.STATUS_ACTIVE:
        return JsonResponse({'error': 'Game is over'}, status=400)

    tile_map = {(t.x, t.y): t for t in game.tiles.select_related('building').all()}
    pieces = list(game.pieces.filter(owner=game.current_player))

    for piece in pieces:
        tile = tile_map.get((piece.x, piece.y))
        if tile and tile.building and tile.building.owner == game.current_player:
            piece.hp = min(piece.max_hp, piece.hp + max(1, piece.max_hp // 5))
        piece.has_moved = False
        piece.has_attacked = False

    Piece.objects.bulk_update(pieces, ['hp', 'has_moved', 'has_attacked'])

    game.current_player = 2 if game.current_player == 1 else 1
    if game.current_player == 1:
        game.turn_number += 1
    game.save(update_fields=['current_player', 'turn_number'])

    return JsonResponse(_serialize_state(game))
