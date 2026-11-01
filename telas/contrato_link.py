"""Link seguro do contrato assinado (enviado por WhatsApp/e-mail): baixa o PDF sem precisar entrar no app."""
import streamlit as st

from core import contrato as ct, repo
from core.fmt import TZ

tok = str(st.query_params.get("contrato", ""))[:40]
c = repo.contrato_por_token(tok)
st.title("📄 Contrato de transporte escolar")
if not c:
    st.error("Link inválido ou contrato não encontrado. Peça um novo link à van.", icon=":material/link_off:")
    st.stop()
emp = repo.empresa(c["condutor_id"])
st.markdown(f"**{c['aluno']}** · {c['ano']} · {emp.get('razao_social') or emp['nome']}")
st.caption(f"Assinado por {c['responsavel_nome']} em {c['responsavel_assinou_em'].astimezone(TZ):%d/%m/%Y %H:%M}"
           + (f" · contratada em {c['contratada_assinou_em'].astimezone(TZ):%d/%m/%Y %H:%M}"
              if c.get("contratada_assinou_em") else " · aguardando a assinatura da contratada")
           + f" · código {c['codigo']}")
st.download_button("Baixar contrato (PDF)", ct.pdf_cache(c, emp), file_name=f"contrato_{c['ano']}.pdf",
                   mime="application/pdf", icon=":material/download:", type="primary")
st.caption("Assinatura eletrônica com validade jurídica (Lei nº 14.063/2020 e art. 10, § 2º, da MP nº 2.200-2/2001).")
