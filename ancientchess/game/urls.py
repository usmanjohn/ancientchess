from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.new_game, name='new_game'),
    path('<int:game_id>/', views.game_view, name='game_view'),
    path('<int:game_id>/state/', views.game_state, name='game_state'),
    path('<int:game_id>/moves/<int:piece_id>/', views.valid_moves, name='valid_moves'),
    path('<int:game_id>/move/', views.move_piece, name='move_piece'),
    path('<int:game_id>/attack/', views.attack_piece, name='attack_piece'),
    path('<int:game_id>/end_turn/', views.end_turn, name='end_turn'),
]
