from sqlalchemy.orm import Session
from redis import Redis
from app.db.models import Conversation, Message
from app.services.guest_session_service import validate_guest_session
from app.services.conversation_memory import push_message, get_context, update_profile
from sqlalchemy import select

def handle_chat_message(
    db: Session, 
    redis: Redis, 
    guest_session_id: str, 
    token: str, 
    message: str
) -> dict:
    
    # 1. Vérifier la session
    session = validate_guest_session(db, guest_session_id, token)
    if not session:
        raise ValueError("Session invalide ou expirée")

    # 2. Trouver ou créer la conversation en base de données
    query = select(Conversation).where(Conversation.guest_session_id == session.id)
    result = db.execute(query)
    conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversation(guest_session_id=session.id, title=message[:50])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    conv_id_str = str(conv.id)

    # 3. Sauvegarder le message de l'utilisateur (Redis + PostgreSQL)
    push_message(redis, conv_id_str, "user", message)
    db_message = Message(conversation_id=conv.id, role="user", content=message)
    db.add(db_message)
    db.commit()

    # 4. Récupérer la mémoire (contexte)
    context = get_context(redis, conv_id_str)
    
    # 5. GÉNÉRATION DE LA RÉPONSE (Mock pour l'instant, le LLM viendra ici)
    # On simule une réponse basée sur le contexte
    if len(context) == 1:
        answer = "Bonjour ! Je suis SmartCampus AI. Quel est votre niveau scolaire actuel (Bac, etc.) ?"
        # On simule l'extraction d'info
        update_profile(redis, conv_id_str, {"status": "en_cours_d_orientation"})
    else:
        answer = f"J'ai bien noté votre message : '{message}'. Pouvez-vous m'en dire plus sur vos matières préférées ?"

    # 6. Sauvegarder la réponse de l'assistant
    push_message(redis, conv_id_str, "assistant", answer)
    db_reply = Message(conversation_id=conv.id, role="assistant", content=answer)
    db.add(db_reply)
    db.commit()

    return {
        "conversation_id": conv_id_str,
        "answer": answer,
        "context_size": len(context)
    }