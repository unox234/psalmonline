from app import db, Liturgiebord
import uuid

with db.app.app_context():
    for board in Liturgiebord.query.filter((Liturgiebord.unique_id == None) | (Liturgiebord.unique_id == '')).all():
        board.unique_id = uuid.uuid4().hex
    db.session.commit()