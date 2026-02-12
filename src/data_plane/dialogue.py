"""Dialogue manager for handling conversations."""

from typing import Any, Dict, Optional

from src.data_plane import DeterministicGenerator, TFIDFRetriever
from src.observability import EventLog, get_logger
from src.state import StateStore
from src.utils import generate_deterministic_seed

logger = get_logger(__name__)


class DialogueManager:
    """Manages conversations with deterministic responses."""

    def __init__(
        self,
        retriever: TFIDFRetriever,
        state_store: StateStore,
        event_log: EventLog,
        seed_salt: str,
        time_bucket_seconds: int,
        max_sentences: int,
        top_k_retrieval: int,
    ) -> None:
        """Initialize dialogue manager."""
        self.retriever = retriever
        self.state_store = state_store
        self.event_log = event_log
        self.seed_salt = seed_salt
        self.time_bucket_seconds = time_bucket_seconds
        self.max_sentences = max_sentences
        self.top_k_retrieval = top_k_retrieval

        logger.info(
            "Dialogue manager initialized",
            seed_salt=seed_salt[:10] + "...",
            time_bucket=time_bucket_seconds,
        )

    def process_message(
        self,
        session_id: str,
        user_input: str,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message and generate a response.

        Args:
            session_id: Session identifier
            user_input: User's input text
            timestamp: Optional timestamp for seed generation

        Returns:
            Dictionary with response and metadata
        """
        # Ensure session exists
        self.state_store.create_session(session_id)
        self.state_store.update_session_activity(session_id)

        # Generate deterministic seed
        seed = generate_deterministic_seed(
            session_id=session_id,
            user_input=user_input,
            salt=self.seed_salt,
            time_bucket_seconds=self.time_bucket_seconds,
            timestamp=timestamp,
        )

        # Store seed
        self.state_store.store_seed(session_id, user_input, seed)

        logger.info("Seed generated", session_id=session_id, seed=seed)

        # Log seed generation event
        self.event_log.log_event(
            "seed_generated",
            {"user_input": user_input, "seed": seed},
            session_id=session_id,
        )

        # Retrieve relevant documents
        try:
            retrieved_docs = self.retriever.retrieve(user_input, top_k=self.top_k_retrieval)
            logger.info(
                "Retrieval complete",
                session_id=session_id,
                num_docs=len(retrieved_docs),
            )

            # Log retrieval event
            self.event_log.log_event(
                "retrieval",
                {
                    "query": user_input,
                    "num_results": len(retrieved_docs),
                    "doc_ids": [doc.get("doc_id") for doc in retrieved_docs],
                },
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f"Retrieval failed: {e}", session_id=session_id)
            return {
                "response": "I apologize, but I encountered an error retrieving information.",
                "seed": seed,
                "error": str(e),
            }

        # Generate response deterministically
        try:
            generator = DeterministicGenerator(seed=seed, max_sentences=self.max_sentences)
            response_text = generator.generate(retrieved_docs)

            logger.info("Response generated", session_id=session_id, seed=seed)

            # Log generation event
            self.event_log.log_event(
                "generation",
                {"seed": seed, "response_length": len(response_text)},
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f"Generation failed: {e}", session_id=session_id)
            return {
                "response": "I apologize, but I encountered an error generating a response.",
                "seed": seed,
                "error": str(e),
            }

        # Log chat event
        self.event_log.log_event(
            "chat",
            {
                "user_input": user_input,
                "response": response_text,
                "seed": seed,
            },
            session_id=session_id,
        )

        return {
            "response": response_text,
            "seed": seed,
            "retrieved_docs": len(retrieved_docs),
        }

    def get_session_history(self, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get conversation history for a session."""
        return self.state_store.get_session_seeds(session_id, limit=limit)
