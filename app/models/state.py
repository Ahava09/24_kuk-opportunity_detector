from app.database import db

class State(db.Model):
    __tablename__ = "state"
    
    id = db.Column(db.Integer, primary_key=True)
    name_state = db.Column(db.String(255), nullable=False, unique=True)

    def __repr__(self):
        return f"<State {self.name_state}>"
    
    def __init__(self, name_state):
        self.name_state = name_state

    def save(self):
        db.session.add(self)
        db.session.commit()

    def to_dict(self):
        """ Convertit un objet Mailstate en dictionnaire JSON """
        return {
            "id": self.id,
            "name_state": self.name_state
        }

    @staticmethod
    def get_all_json():
        """ Récupère tous les Mailstate sous forme de JSON """
        states = State.query.all()
        return [state.to_dict() for state in states]


    @classmethod
    def get_all_states(cls):
        """Récupérer tous les états"""
        return cls.query.all()

    @classmethod
    def get_state_by_id(cls, state_id):
        """Récupérer un état par son ID"""
        return cls.query.get(state_id)

    @classmethod
    def add_state(cls, name_state):
        """Ajouter un nouvel état"""
        new_state = cls(name_state=name_state)
        db.session.add(new_state)
        db.session.commit()
        return new_state
    
    # @classmethod
    # def exists(cls, name_state):
    #     existing_state = cls.query.filter_by(name_state=name_state).first()
    #     return existing_state is not None  

    @staticmethod
    def default():
        print("🔍 Démarrage de la fonction default()")
        
        # Chercher le state par défaut
        default_state = State.query.filter_by(name_state="Nouveau Client").first()
        
        # Si aucun state trouvé, insérer "Nouveau Client" par défaut
        if not default_state:
            default_state = State(name_state="Nouveau Client")
            try:
                print("🔔 Tentative d'insertion du state 'Nouveau Client' dans la base de données...")
                db.session.add(default_state)
                db.session.commit()
                db.session.refresh(default_state)
                print(f"🔔 State '{default_state.name_state}' inséré avec ID {default_state.id}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur lors de l'insertion : {e}")
                return None
        
        print(f"🔔 Retour de l'ID du state : {default_state.id}")
        return default_state.id

    @staticmethod
    def is_partner():
        default_state = State.query.filter_by(name_state="Accepté").first()
        
        if not default_state:
            default_state = State(name_state="Accepté")
            try:
                db.session.add(default_state)
                db.session.commit()
                print(f"🔔 State '{default_state.name_state}' inséré avec ID {default_state.id}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur lors de l'insertion : {e}")
                return None
        
        return default_state.id
