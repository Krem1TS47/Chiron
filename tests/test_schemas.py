from chiron.ingestion.schemas import PlayerSchema, ShotEventSchema


def test_player_schema():
    player = PlayerSchema(id=2544, full_name="LeBron James", position="F")
    assert player.id == 2544
    assert player.is_active is True


def test_shot_event_schema():
    shot = ShotEventSchema(
        player_id=1,
        game_id="0022300001",
        event_num=0,
        x=100.0,
        y=200.0,
        shot_made=True,
    )
    assert shot.shot_made is True
