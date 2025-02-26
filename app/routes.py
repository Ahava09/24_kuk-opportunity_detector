from flask import Blueprint, jsonify, render_template, request, jsonify
from app.models.email_client import Email
from app.database import db
from sqlalchemy import cast, String

api_emails_blueprint = Blueprint('api_emails', __name__)

@api_emails_blueprint.route("/emails", methods=["GET"])
def get_emails():
    try:

        with db.session.begin():
            emails = Email.query.all()
            
            if not emails:
                return jsonify({"message": "No emails found"}), 404
            
            return jsonify([{
                "id": email.id,
                "subject": email.subject,
                "receive_date": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
                "path": email.path,
                "is_negoce": email.is_negoce
            } for email in emails])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @api_emails_blueprint.route("/searchCriteria", methods=["GET"])
# def search_emails():
    # search_term = request.args.get("criterion", "").strip()

    # if not search_term:
    #     render_template("email.html")

    # matching_emails = Email.query.filter(
    #     (Email.subject.ilike(f"%{search_term}%")) |
    #     (Email.body.ilike(f"%{search_term}%"))|
    #     (Email.sender.ilike(f"%{search_term}%"))|
    #     (cast(Email.receive_at, String).ilike(f"%{search_term}%"))
    # ).all()
    # print(search_term)

    # if not matching_emails:
    #     return jsonify({"error": "Aucun email trouvé"}), 404

    # emails_json = [{
    #     "id": email.id,
    #     "subject": email.subject,
    #     "from": email.sender,
    #     "body": email.body,
    #     "receive_at": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
    #     "is_negoce": email.is_negoce
    # } for email in matching_emails]

    # return jsonify({"emails": emails_json, "count": len(emails_json)})

    
@api_emails_blueprint.route("/searchCriteria", methods=["GET"])
def search_criterion():
    search_term = request.args.get("criterion", "").strip()
    print(search_term)
    message = Email.message_chat(search_term)
    print(message)
    return jsonify({"message": message})