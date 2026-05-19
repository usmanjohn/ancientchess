from django.db import models


class GameSession(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES = [(STATUS_ACTIVE, 'Active'), (STATUS_FINISHED, 'Finished')]

    current_player = models.IntegerField(default=1)
    turn_number = models.IntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    winner = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game {self.pk} — Player {self.current_player}'s turn ({self.status})"


class Building(models.Model):
    TYPE_CASTLE = 'castle'
    TYPE_HOUSE = 'house'
    TYPE_CHOICES = [(TYPE_CASTLE, 'Castle'), (TYPE_HOUSE, 'House')]

    game = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='buildings')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    owner = models.IntegerField(null=True, blank=True)  # 1, 2, or null
    hp = models.IntegerField(default=20)

    def __str__(self):
        return f"{self.type} owned by {self.owner} (Game {self.game_id})"


class Tile(models.Model):
    TERRAIN_PLAINS = 'plains'
    TERRAIN_FOREST = 'forest'
    TERRAIN_MOUNTAIN = 'mountain'
    TERRAIN_WATER = 'water'
    TERRAIN_ROAD = 'road'
    TERRAIN_CHOICES = [
        (TERRAIN_PLAINS, 'Plains'),
        (TERRAIN_FOREST, 'Forest'),
        (TERRAIN_MOUNTAIN, 'Mountain'),
        (TERRAIN_WATER, 'Water'),
        (TERRAIN_ROAD, 'Road'),
    ]

    game = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='tiles')
    x = models.IntegerField()
    y = models.IntegerField()
    terrain_type = models.CharField(max_length=10, choices=TERRAIN_CHOICES, default=TERRAIN_PLAINS)
    building = models.OneToOneField(
        Building, on_delete=models.SET_NULL, null=True, blank=True, related_name='tile'
    )

    class Meta:
        unique_together = ('game', 'x', 'y')

    def __str__(self):
        return f"Tile ({self.x},{self.y}) {self.terrain_type} (Game {self.game_id})"


class Piece(models.Model):
    TYPE_KING = 'king'
    TYPE_QUEEN = 'queen'
    TYPE_ROOK = 'rook'
    TYPE_BISHOP = 'bishop'
    TYPE_KNIGHT = 'knight'
    TYPE_PAWN = 'pawn'
    TYPE_CHOICES = [
        (TYPE_KING, 'King'), (TYPE_QUEEN, 'Queen'), (TYPE_ROOK, 'Rook'),
        (TYPE_BISHOP, 'Bishop'), (TYPE_KNIGHT, 'Knight'), (TYPE_PAWN, 'Pawn'),
    ]

    STATS = {
        TYPE_PAWN:   {'hp': 20, 'attack': 8,  'defense': 3, 'move_points': 2},
        TYPE_KNIGHT: {'hp': 25, 'attack': 12, 'defense': 4, 'move_points': 3},
        TYPE_BISHOP: {'hp': 22, 'attack': 10, 'defense': 3, 'move_points': 4},
        TYPE_ROOK:   {'hp': 30, 'attack': 14, 'defense': 5, 'move_points': 4},
        TYPE_QUEEN:  {'hp': 35, 'attack': 16, 'defense': 6, 'move_points': 5},
        TYPE_KING:   {'hp': 40, 'attack': 10, 'defense': 8, 'move_points': 2},
    }

    game = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='pieces')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    owner = models.IntegerField()  # 1 or 2
    x = models.IntegerField()
    y = models.IntegerField()
    hp = models.IntegerField()
    max_hp = models.IntegerField()
    attack = models.IntegerField()
    defense = models.IntegerField()
    move_points = models.IntegerField()
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    has_moved = models.BooleanField(default=False)
    has_attacked = models.BooleanField(default=False)

    def __str__(self):
        return f"P{self.owner} {self.type} at ({self.x},{self.y}) HP:{self.hp} (Game {self.game_id})"
