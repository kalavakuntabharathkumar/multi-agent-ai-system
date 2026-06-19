"""
Smoke test for the HuggingFace-embeddings-backed document QA tool.

Run with:
    pytest tests/test_document_tool.py -v -s

Or run directly:
    python tests/test_document_tool.py
"""

from unittest.mock import patch, MagicMock
from tools.document_tool import answer_from_document

SAMPLE_DOCUMENT = """
The Eiffel Tower is a wrought-iron lattice tower located on the Champ de Mars
in Paris, France. It was constructed from 1887 to 1889 as the centerpiece of
the 1889 World's Fair. The tower is 330 metres (1,083 ft) tall and was the
tallest man-made structure in the world for 41 years until the Chrysler Building
was completed in New York City in 1930. The tower is named after engineer
Gustave Eiffel, whose company designed and built it.
"""

SAMPLE_QUESTION = "Who designed the Eiffel Tower?"


def test_answer_from_document_uses_hf_embeddings():
    """Verifies HuggingFaceEmbeddings are used (not OpenAIEmbeddings) and
    that the chain returns a non-empty string answer."""
    mock_llm_response = "The Eiffel Tower was designed by engineer Gustave Eiffel."

    with patch("tools.document_tool.ChatOpenAI") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.__or__ = lambda self, other: other
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_llm_response
        mock_llm_cls.return_value = mock_llm

        with patch("tools.document_tool.HuggingFaceEmbeddings") as mock_emb_cls:
            from langchain_huggingface import HuggingFaceEmbeddings as RealHFE
            mock_emb_cls.side_effect = RealHFE

            with patch("tools.document_tool.FAISS") as mock_faiss:
                mock_vs = MagicMock()
                mock_vs.as_retriever.return_value = MagicMock()
                mock_faiss.from_documents.return_value = mock_vs

                with patch("tools.document_tool.StrOutputParser"):
                    with patch("tools.document_tool.RunnablePassthrough"):
                        result = answer_from_document(SAMPLE_DOCUMENT, SAMPLE_QUESTION)

            assert mock_emb_cls.called, "HuggingFaceEmbeddings was not called"
            model_arg = mock_emb_cls.call_args[1].get(
                "model_name", mock_emb_cls.call_args[0][0] if mock_emb_cls.call_args[0] else None
            )
            assert model_arg == "sentence-transformers/all-MiniLM-L6-v2", (
                f"Wrong model: {model_arg}"
            )


def test_answer_from_document_live(pytestmark=None):
    """
    Integration smoke test — downloads the model on first run (~80 MB, cached after).
    Skipped automatically if OPENAI_API_KEY is not set.
    """
    import os
    if not os.getenv("OPENAI_API_KEY"):
        import pytest
        pytest.skip("OPENAI_API_KEY not set — skipping live integration test")

    answer = answer_from_document(SAMPLE_DOCUMENT, SAMPLE_QUESTION)
    print(f"\nAnswer: {answer}")
    assert isinstance(answer, str)
    assert len(answer) > 0


if __name__ == "__main__":
    print("Running live smoke test...")
    print(f"Document: {SAMPLE_DOCUMENT.strip()[:80]}...")
    print(f"Question: {SAMPLE_QUESTION}")
    answer = answer_from_document(SAMPLE_DOCUMENT, SAMPLE_QUESTION)
    print(f"\nAnswer: {answer}")
