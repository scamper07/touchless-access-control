from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import null
import random

app = Flask(__name__)
app.debug = True

# sqlite database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tac.db'

db = SQLAlchemy(app)

selected_lock=null

# enable Foreign Key constraint
def _fk_pragma_on_connect(dbapi_con, con_record):  # noqa
    dbapi_con.execute('pragma foreign_keys=ON')

with app.app_context():
    from sqlalchemy import event
    event.listen(db.engine, 'connect', _fk_pragma_on_connect)

# Models
class Locks(db.Model):
	__tablename__ = 'locks'
	LockID = db.Column(db.Integer, primary_key=True)
	LockName = db.Column(db.String(64), unique=True, nullable=False)
	keys = db.relationship("Keys", backref="locks", lazy="dynamic")

	def __init__(self, LockID, LockName):
		self.LockID = LockID
		self.LockName = LockName	
    
	@property
	def serialized(self):
		return {
            'id': self.LockID,
            'name': self.LockName,
        }

class Keys(db.Model):	
	__tablename__ = 'keys'
	__table_args__ = {'sqlite_autoincrement': True}
	KeyID = db.Column(db.Integer, primary_key=True, nullable=True)
	KeyValue = db.Column(db.String(128), unique=True, nullable=False)
	LockID = db.Column(db.Integer, db.ForeignKey('locks.LockID'), nullable=False)

	def __init__(self, KeyID, KeyValue, LockID):
		self.KeyID = KeyID
		self.KeyValue = KeyValue
		self.LockID = LockID

	@property
	def serialized(self):
		return {
            'id': self.KeyID,
            'value': self.KeyValue,
            'lockid': self.LockID,
        }

# APIs
@app.route('/api/getlock', methods = ['GET'])
def get_locks():
    try:
        if request.method == 'GET':
            locks = Locks.query.all()
            return jsonify({'data': [lock.serialized for lock in locks]})
        else:
            return jsonify({'data': 'fail'})
    except Exception as e:
        print(e)
        return jsonify({'data': 'fail'})

@app.route('/api/getkey', defaults={'lockid': None}, methods = ['GET'])
@app.route('/api/getkey/<lockid>', methods = ['GET'])
def get_keys(lockid):
    try:
        if request.method == 'GET':
            if not lockid:
                keys = Keys.query.all()            
            else:
                keys = Keys.query.filter_by(LockID = lockid).all()
            return jsonify({'data': [key.serialized for key in keys]})
        else:
            return jsonify({'data': 'fail'})
    except Exception as e:
        print(e)
        return jsonify({'data': 'fail'})

@app.route('/api/addkey', methods = ['POST'])
def add_keys():
    try:
        if request.method == 'POST':
            content = request.json
            key_id = content['id']
            key_value = content['value']
            lock_id = content['lockid']
            
            db.session.add(Keys(key_id, key_value, lock_id))
            db.session.commit()
            return jsonify({'data': "success"})
        else:
            return jsonify({'data': 'fail'})
    except Exception as e:
        print(e)
        return jsonify({'data': 'fail'})

@app.route('/api/deletekey/<keyid>', methods = ['GET'])
def delete_key(keyid):
    try:
        if request.method == 'GET':
            key = Keys.query.filter_by(KeyID=keyid).first()        
            db.session.delete(key)
            db.session.commit()        
            return jsonify({'data': "success"})
        else:
            return jsonify({'data': 'fail'})
    except Exception as e:
        print(e)
        return jsonify({'data': 'fail'})

#web app
@app.route("/", methods=['GET', 'POST'])
def index():
    selected_lock = 0
    locks = Locks.query.all()
    data = [lock.serialized for lock in locks]
    
    data_keys=null
    
    if request.method == 'POST':
        if request.form.get('refresh'):
            print("In Refresh...")
            selected_lock = request.form.get('selectedlock')
            print(selected_lock)
            keys = Keys.query.filter_by(LockID=selected_lock).all()                                                                                           
            data_keys = [key.serialized for key in keys]
            print(data_keys)
            return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock)
        elif request.form.get('deletekey'):
            print("In Delete Key...")
            selected_lock = request.form.get('selectedlock')
            deletekey_id = request.form.get('keyid')
            key = Keys.query.filter_by(KeyID=deletekey_id).first()        
            db.session.delete(key)
            db.session.commit()            
            keys = Keys.query.filter_by(LockID=selected_lock).all()
            data_keys = [key.serialized for key in keys]
            return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock)
        elif request.form.get('addkey'):
            print("In Add Key...")
            print(request.form.get('newkey'), request.form.get('selectedlock'))
            selected_lock = request.form.get('selectedlock')
            id = random.randrange(100,2000)
            db.session.add(Keys(KeyID=id,KeyValue=request.form.get('newkey'), LockID=request.form.get('selectedlock')))
            db.session.commit()
            keys = Keys.query.filter_by(LockID=selected_lock).all()                                                                                           
            data_keys = [key.serialized for key in keys]
            return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock)
        else:            
            return render_template("index.html")
    elif request.method == 'GET':                                                                                                       
        return render_template("index.html", data=data, selected_lock=selected_lock)
    
if __name__ == '__main__':
	app.run()
