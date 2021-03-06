from operator import xor
from flask import Flask, flash, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import null

app = Flask(__name__)
app.debug = True

# sqlite database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tac.db'

db = SQLAlchemy(app)

selected_lock_backup=None

MASTER_KEY="73737373A5A5A5A5373737375A5A5A5A"

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
	TagID = db.Column(db.String(8), unique=True, primary_key=True, nullable=True)
	KeyValue = db.Column(db.String(128), unique=True, nullable=False)
	IsActive = db.Column(db.Integer, nullable=False)
	LockID = db.Column(db.Integer, db.ForeignKey('locks.LockID'), nullable=False)

	def __init__(self, TagID, KeyValue, IsActive, LockID):
		self.TagID = TagID
		self.KeyValue = KeyValue
		self.IsActive = IsActive
		self.LockID = LockID

	@property
	def serialized(self):
		return {
            'id': self.TagID,
            'value': self.KeyValue,
            'lockid': self.LockID,
            'isactive': self.IsActive
        }

# Utils
def change_to_be_hex(s):
    return int(s,base=16)
    
def xor_two_str(str1,str2):
    a = change_to_be_hex(str1)
    b = change_to_be_hex(str2)
    return hex(a ^ b)[2:].upper()

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
    return_value = ""
    try:
        if request.method == 'GET':
            if not lockid:
                keys = Keys.query.all()            
            else:
                keys = Keys.query.filter_by(LockID = lockid, IsActive=1).all()

                if len(keys) < 1:
                    return "404", 404 
                            
                for key in keys:
                    return_value += key.TagID + key.KeyValue
            #return jsonify({'data': [key.serialized for key in keys]})
            return return_value
        else:
            return "404", 404 
    except Exception as e:
        print(e)
        return "404", 404 

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
    global selected_lock_backup

    selected_lock = 0
    locks = Locks.query.all()
    data = [lock.serialized for lock in locks]
    
    data_keys=null
    try:
        if request.method == 'POST':
            if request.form.get('refresh'):
                print("In Refresh...")
                selected_lock = request.form.get('selectedlock')
                print(selected_lock)
                selected_lock_backup = selected_lock
                keys = Keys.query.filter_by(LockID=selected_lock).all()                                                                                           
                data_keys = [key.serialized for key in keys]
                print(data_keys)
                return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock)
            elif request.form.get('deletekey'):
                print("In Delete Key...")
                selected_lock = request.form.get('selectedlock')
                deletekey_id = request.form.get('deletekey')
                key = Keys.query.filter_by(TagID=deletekey_id).first()        
                db.session.delete(key)
                db.session.commit()            
                keys = Keys.query.filter_by(LockID=selected_lock_backup).all()
                data_keys = [key.serialized for key in keys]
                return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock_backup)
            elif request.form.get('addkey'):
                print("In Add Key...")
                new_key = request.form.get('newkey')
                print(new_key)
                new_key = new_key*4                    
                new_key = xor_two_str(new_key, MASTER_KEY)
                print(new_key)
                selected_lock = request.form.get('selectedlock')
                db.session.add(Keys(TagID=request.form.get('newkey').upper(),KeyValue=new_key, LockID=request.form.get('selectedlock'), IsActive=1)) #by default Key is activated
                db.session.commit()

                keys = Keys.query.filter_by(LockID=selected_lock).all()                                                                                           
                data_keys = [key.serialized for key in keys]
                return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock)
            else:  
                print("In toggle Key...")
                print(request.form['togglekeyid'])
                toggle_key =request.form['togglekeyid']
                keys = Keys.query.filter_by(TagID=toggle_key).first()
                toggle_key_isactive = keys.IsActive

                if toggle_key_isactive == 1:
                    keys.IsActive = 0
                else:
                    keys.IsActive = 1

                db.session.commit()      
                keys = Keys.query.filter_by(LockID=selected_lock_backup).all()                                                                                           
                data_keys = [key.serialized for key in keys]                                                                                                
                return render_template("index.html", data=data, keys=data_keys, selected_lock=selected_lock_backup)
        elif request.method == 'GET':                                                                                                       
            return render_template("index.html", data=data, selected_lock=selected_lock)
    except Exception as e:
        print(e)
        error_message=""
        if "UNIQUE constraint failed" in str(e):
            error_message = "Please Enter Unique TagID"
        return render_template("index.html", data=data, selected_lock=selected_lock, error_message=error_message)
    
if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8080)
