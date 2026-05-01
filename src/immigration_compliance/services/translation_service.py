"""Translation Service — multi-language UI strings + attorney-client message translation.

Two surfaces:

  1. UI STRINGS — Static phrase library for applicant-facing labels,
     buttons, and instructional copy. Loaded into the frontend at page
     boot. Six target languages (zh, es, hi, ar, fr, pt) plus English.

  2. AD-HOC TRANSLATION — Translates arbitrary attorney→client and
     client→attorney messages with explicit disclaimers ("AI-assisted
     translation; English version is the legal record"). The legal
     record always stays in English. The translation is for client
     convenience only.

Production: ad-hoc translation calls an LLM provider (DeepL / Google
Translate / Anthropic / etc.). The dispatcher boundary is stable so
swap is a one-method change. This implementation returns deterministic
templated translations for development + tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# UI phrase library
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = ("en", "zh", "es", "hi", "ar", "fr", "pt")
RTL_LANGUAGES = ("ar",)
LANGUAGE_NAMES = {
    "en": "English", "zh": "中文 (Mandarin)", "es": "Español",
    "hi": "हिन्दी (Hindi)", "ar": "العربية (Arabic)",
    "fr": "Français", "pt": "Português",
}

# Applicant-facing UI strings. Keys are stable; English is the source.
UI_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Onboarding wizard
        "onboarding_welcome": "What's your immigration goal?",
        "onboarding_welcome_sub": "We'll personalize the rest of this experience based on your goal. Your answers stay private.",
        "onboarding_destination": "Where are you headed?",
        "onboarding_destination_sub": "Pick your destination country.",
        "onboarding_visa_recommendations": "Recommended visa types",
        "onboarding_visa_recommendations_sub": "Based on your goal and destination, here's what fits.",
        "onboarding_eligibility": "Eligibility check",
        "onboarding_eligibility_sub": "Quick yes/no questions for your visa type. We'll surface any blockers immediately.",
        "onboarding_strength": "Your case strength",
        "onboarding_strength_sub": "Based on your answers, here's where you stand. This is rules-based AI — every factor is explainable.",
        "onboarding_documents": "Your personalized document checklist",
        "onboarding_documents_sub": "Based on your answers, you'll need these specific documents.",
        "onboarding_attorneys": "Verified attorneys ready to help",
        "onboarding_attorneys_sub": "We've matched you with attorneys whose specialization, jurisdiction, and capacity fit your case.",
        # Goals
        "goal_student": "Student",
        "goal_student_desc": "Study at a university, college, or language school",
        "goal_work": "Work",
        "goal_work_desc": "Employment, transfer, or specialty occupation",
        "goal_family": "Family / Spouse",
        "goal_family_desc": "Join family or marry abroad",
        "goal_pr": "Permanent Residency",
        "goal_pr_desc": "Green Card, ILR, PR, citizenship pathway",
        "goal_investor": "Investor / Entrepreneur",
        "goal_investor_desc": "Build a business or invest abroad",
        # Common UI
        "btn_continue": "Continue →",
        "btn_back": "← Back",
        "btn_yes": "Yes",
        "btn_no": "No",
        "btn_submit": "Submit",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "btn_open_uploader": "Open uploader →",
        "btn_save_continue": "Save & continue to dashboard →",
        "label_required": "*",
        "label_step_of": "Step {current} of {total}",
        "compliance_banner": "Verom is a technology platform — we organize information and help you connect with verified attorneys. Verom does not provide legal advice. Your data is encrypted and never shared without your consent.",
        # Status pills
        "status_intake": "Intake",
        "status_documents": "Documents",
        "status_review": "Review",
        "status_filed": "Filed",
        "status_rfe": "RFE",
        "status_approved": "Approved",
        "status_denied": "Denied",
        # Strength tiers
        "tier_excellent": "EXCELLENT",
        "tier_strong": "STRONG",
        "tier_moderate": "MODERATE",
        "tier_weak": "WEAK",
        # Document collection
        "docs_completeness": "Completeness",
        "docs_no_uploads": "No documents uploaded yet",
        "docs_drop_here": "Drop files here or click to upload",
        "docs_required_documents": "Required documents",
    },
    "zh": {
        "onboarding_welcome": "您的移民目标是什么?",
        "onboarding_welcome_sub": "我们会根据您的目标个性化整个流程。您的答案保持私密。",
        "onboarding_destination": "您要去哪里?",
        "onboarding_destination_sub": "选择您的目的地国家。",
        "onboarding_visa_recommendations": "推荐的签证类型",
        "onboarding_visa_recommendations_sub": "根据您的目标和目的地,这里是合适的选项。",
        "onboarding_eligibility": "资格检查",
        "onboarding_eligibility_sub": "快速回答有关您签证类型的是/否问题。我们会立即发现任何障碍。",
        "onboarding_strength": "您的案件实力",
        "onboarding_strength_sub": "根据您的答案,这是您目前的状态。这是基于规则的AI——每个因素都可以解释。",
        "onboarding_documents": "您的个性化文件清单",
        "onboarding_documents_sub": "根据您的答案,您将需要这些特定文件。",
        "onboarding_attorneys": "经过认证的律师准备帮助您",
        "onboarding_attorneys_sub": "我们为您匹配了专业、辖区和能力符合您案件的律师。",
        "goal_student": "学生",
        "goal_student_desc": "在大学、学院或语言学校学习",
        "goal_work": "工作",
        "goal_work_desc": "就业、调动或专业职业",
        "goal_family": "家庭 / 配偶",
        "goal_family_desc": "与家人团聚或在国外结婚",
        "goal_pr": "永久居留权",
        "goal_pr_desc": "绿卡、ILR、PR、入籍途径",
        "goal_investor": "投资者 / 企业家",
        "goal_investor_desc": "在国外建立企业或投资",
        "btn_continue": "继续 →",
        "btn_back": "← 返回",
        "btn_yes": "是",
        "btn_no": "否",
        "btn_submit": "提交",
        "btn_save": "保存",
        "btn_cancel": "取消",
        "btn_open_uploader": "打开上传器 →",
        "btn_save_continue": "保存并继续到仪表板 →",
        "label_required": "*",
        "label_step_of": "第 {current} 步,共 {total} 步",
        "compliance_banner": "Verom 是一个技术平台——我们整理信息并帮助您与经过认证的律师联系。Verom 不提供法律建议。您的数据已加密,未经您同意不会共享。",
        "status_intake": "录入中",
        "status_documents": "文件",
        "status_review": "审核中",
        "status_filed": "已提交",
        "status_rfe": "证据请求",
        "status_approved": "已批准",
        "status_denied": "已拒绝",
        "tier_excellent": "优秀",
        "tier_strong": "强",
        "tier_moderate": "中等",
        "tier_weak": "弱",
        "docs_completeness": "完成度",
        "docs_no_uploads": "尚未上传文件",
        "docs_drop_here": "将文件拖至此处或点击上传",
        "docs_required_documents": "必需文件",
    },
    "es": {
        "onboarding_welcome": "¿Cuál es su objetivo migratorio?",
        "onboarding_welcome_sub": "Personalizaremos el resto de la experiencia según su objetivo. Sus respuestas son privadas.",
        "onboarding_destination": "¿Hacia dónde se dirige?",
        "onboarding_destination_sub": "Elija su país de destino.",
        "onboarding_visa_recommendations": "Tipos de visa recomendados",
        "onboarding_visa_recommendations_sub": "Según su objetivo y destino, esto es lo que se ajusta.",
        "onboarding_eligibility": "Verificación de elegibilidad",
        "onboarding_eligibility_sub": "Preguntas rápidas de sí/no sobre su tipo de visa. Detectaremos cualquier bloqueo inmediatamente.",
        "onboarding_strength": "La fortaleza de su caso",
        "onboarding_strength_sub": "Según sus respuestas, esta es su situación. Es IA basada en reglas — cada factor es explicable.",
        "onboarding_documents": "Su lista de documentos personalizada",
        "onboarding_documents_sub": "Según sus respuestas, necesitará estos documentos específicos.",
        "onboarding_attorneys": "Abogados verificados listos para ayudarle",
        "onboarding_attorneys_sub": "Le hemos emparejado con abogados cuya especialización, jurisdicción y capacidad se ajustan a su caso.",
        "goal_student": "Estudiante",
        "goal_student_desc": "Estudiar en universidad, colegio o escuela de idiomas",
        "goal_work": "Trabajo",
        "goal_work_desc": "Empleo, traslado u ocupación especializada",
        "goal_family": "Familia / Cónyuge",
        "goal_family_desc": "Reunirse con familiares o casarse en el extranjero",
        "goal_pr": "Residencia Permanente",
        "goal_pr_desc": "Green Card, ILR, PR, vía a la ciudadanía",
        "goal_investor": "Inversor / Emprendedor",
        "goal_investor_desc": "Crear un negocio o invertir en el extranjero",
        "btn_continue": "Continuar →",
        "btn_back": "← Volver",
        "btn_yes": "Sí",
        "btn_no": "No",
        "btn_submit": "Enviar",
        "btn_save": "Guardar",
        "btn_cancel": "Cancelar",
        "btn_open_uploader": "Abrir cargador →",
        "btn_save_continue": "Guardar y continuar al panel →",
        "label_required": "*",
        "label_step_of": "Paso {current} de {total}",
        "compliance_banner": "Verom es una plataforma tecnológica — organizamos información y le ayudamos a conectar con abogados verificados. Verom no proporciona asesoramiento legal. Sus datos están cifrados y nunca se comparten sin su consentimiento.",
        "status_intake": "Admisión",
        "status_documents": "Documentos",
        "status_review": "Revisión",
        "status_filed": "Presentado",
        "status_rfe": "RFE",
        "status_approved": "Aprobado",
        "status_denied": "Denegado",
        "tier_excellent": "EXCELENTE",
        "tier_strong": "FUERTE",
        "tier_moderate": "MODERADO",
        "tier_weak": "DÉBIL",
        "docs_completeness": "Completitud",
        "docs_no_uploads": "Aún no se han cargado documentos",
        "docs_drop_here": "Arrastre archivos aquí o haga clic para cargar",
        "docs_required_documents": "Documentos requeridos",
    },
    "hi": {
        "onboarding_welcome": "आपका इमिग्रेशन लक्ष्य क्या है?",
        "onboarding_welcome_sub": "हम आपके लक्ष्य के आधार पर बाकी अनुभव को निजीकृत करेंगे। आपके उत्तर निजी रहेंगे।",
        "onboarding_destination": "आप कहाँ जा रहे हैं?",
        "onboarding_destination_sub": "अपना गंतव्य देश चुनें।",
        "onboarding_visa_recommendations": "अनुशंसित वीज़ा प्रकार",
        "onboarding_visa_recommendations_sub": "आपके लक्ष्य और गंतव्य के आधार पर, यहाँ उपयुक्त विकल्प हैं।",
        "onboarding_eligibility": "पात्रता जाँच",
        "onboarding_eligibility_sub": "आपके वीज़ा प्रकार के लिए त्वरित हाँ/नहीं प्रश्न। हम तुरंत किसी भी बाधा को सामने लाएँगे।",
        "onboarding_strength": "आपके केस की मजबूती",
        "onboarding_strength_sub": "आपके उत्तरों के आधार पर, यह आपकी स्थिति है। यह नियम-आधारित AI है — हर कारक व्याख्या योग्य है।",
        "onboarding_documents": "आपकी व्यक्तिगत दस्तावेज़ चेकलिस्ट",
        "onboarding_documents_sub": "आपके उत्तरों के आधार पर, आपको ये विशिष्ट दस्तावेज़ चाहिए होंगे।",
        "onboarding_attorneys": "सत्यापित वकील मदद के लिए तैयार",
        "onboarding_attorneys_sub": "हमने आपको ऐसे वकीलों से मिलाया है जिनकी विशेषज्ञता, क्षेत्राधिकार और क्षमता आपके केस के अनुकूल है।",
        "goal_student": "छात्र",
        "goal_student_desc": "विश्वविद्यालय, कॉलेज या भाषा स्कूल में अध्ययन",
        "goal_work": "कार्य",
        "goal_work_desc": "रोजगार, स्थानांतरण या विशेषज्ञ व्यवसाय",
        "goal_family": "परिवार / जीवनसाथी",
        "goal_family_desc": "परिवार से जुड़ें या विदेश में विवाह करें",
        "goal_pr": "स्थायी निवास",
        "goal_pr_desc": "ग्रीन कार्ड, ILR, PR, नागरिकता मार्ग",
        "goal_investor": "निवेशक / उद्यमी",
        "goal_investor_desc": "विदेश में व्यवसाय बनाएँ या निवेश करें",
        "btn_continue": "जारी रखें →",
        "btn_back": "← पीछे",
        "btn_yes": "हाँ",
        "btn_no": "नहीं",
        "btn_submit": "जमा करें",
        "btn_save": "सहेजें",
        "btn_cancel": "रद्द करें",
        "btn_open_uploader": "अपलोडर खोलें →",
        "btn_save_continue": "सहेजें और डैशबोर्ड पर जारी रखें →",
        "label_required": "*",
        "label_step_of": "चरण {current} / {total}",
        "compliance_banner": "Verom एक तकनीकी प्लेटफ़ॉर्म है — हम जानकारी व्यवस्थित करते हैं और आपको सत्यापित वकीलों से जोड़ने में मदद करते हैं। Verom कानूनी सलाह प्रदान नहीं करता। आपका डेटा एन्क्रिप्टेड है और आपकी सहमति के बिना साझा नहीं किया जाता।",
        "status_intake": "इनटेक",
        "status_documents": "दस्तावेज़",
        "status_review": "समीक्षा",
        "status_filed": "दायर",
        "status_rfe": "RFE",
        "status_approved": "अनुमोदित",
        "status_denied": "अस्वीकृत",
        "tier_excellent": "उत्कृष्ट",
        "tier_strong": "मजबूत",
        "tier_moderate": "मध्यम",
        "tier_weak": "कमजोर",
        "docs_completeness": "पूर्णता",
        "docs_no_uploads": "अभी तक कोई दस्तावेज़ अपलोड नहीं किया गया",
        "docs_drop_here": "फ़ाइलें यहाँ छोड़ें या अपलोड करने के लिए क्लिक करें",
        "docs_required_documents": "आवश्यक दस्तावेज़",
    },
    "ar": {
        "onboarding_welcome": "ما هو هدفك في الهجرة؟",
        "onboarding_welcome_sub": "سنقوم بتخصيص بقية التجربة بناءً على هدفك. تبقى إجاباتك خاصة.",
        "onboarding_destination": "إلى أين تتجه؟",
        "onboarding_destination_sub": "اختر بلد الوجهة.",
        "onboarding_visa_recommendations": "أنواع التأشيرات الموصى بها",
        "onboarding_visa_recommendations_sub": "بناءً على هدفك ووجهتك، إليك ما يناسبك.",
        "onboarding_eligibility": "فحص الأهلية",
        "onboarding_eligibility_sub": "أسئلة سريعة بنعم/لا حول نوع تأشيرتك. سنكشف عن أي عوائق فوراً.",
        "onboarding_strength": "قوة قضيتك",
        "onboarding_strength_sub": "بناءً على إجاباتك، هذا هو وضعك. هذا ذكاء اصطناعي قائم على القواعد — كل عامل قابل للتفسير.",
        "onboarding_documents": "قائمة وثائقك الشخصية",
        "onboarding_documents_sub": "بناءً على إجاباتك، ستحتاج إلى هذه الوثائق المحددة.",
        "onboarding_attorneys": "محامون موثقون جاهزون للمساعدة",
        "onboarding_attorneys_sub": "وفّقناك مع محامين يناسب تخصصهم واختصاصهم وقدرتهم قضيتك.",
        "goal_student": "طالب",
        "goal_student_desc": "الدراسة في جامعة أو كلية أو مدرسة لغات",
        "goal_work": "عمل",
        "goal_work_desc": "توظيف أو نقل أو مهنة متخصصة",
        "goal_family": "عائلة / زوج",
        "goal_family_desc": "الانضمام إلى العائلة أو الزواج في الخارج",
        "goal_pr": "إقامة دائمة",
        "goal_pr_desc": "البطاقة الخضراء، ILR، PR، مسار الجنسية",
        "goal_investor": "مستثمر / رائد أعمال",
        "goal_investor_desc": "بناء عمل أو استثمار في الخارج",
        "btn_continue": "متابعة ←",
        "btn_back": "→ رجوع",
        "btn_yes": "نعم",
        "btn_no": "لا",
        "btn_submit": "إرسال",
        "btn_save": "حفظ",
        "btn_cancel": "إلغاء",
        "btn_open_uploader": "فتح المرفق ←",
        "btn_save_continue": "حفظ ومتابعة إلى لوحة التحكم ←",
        "label_required": "*",
        "label_step_of": "الخطوة {current} من {total}",
        "compliance_banner": "Verom منصة تقنية — نقوم بتنظيم المعلومات ونساعدك على التواصل مع محامين موثقين. Verom لا يقدم استشارات قانونية. بياناتك مشفرة ولا يتم مشاركتها دون موافقتك.",
        "status_intake": "تسجيل",
        "status_documents": "الوثائق",
        "status_review": "مراجعة",
        "status_filed": "مقدم",
        "status_rfe": "RFE",
        "status_approved": "معتمد",
        "status_denied": "مرفوض",
        "tier_excellent": "ممتاز",
        "tier_strong": "قوي",
        "tier_moderate": "متوسط",
        "tier_weak": "ضعيف",
        "docs_completeness": "الاكتمال",
        "docs_no_uploads": "لم يتم تحميل أي وثائق بعد",
        "docs_drop_here": "اسحب الملفات هنا أو انقر للتحميل",
        "docs_required_documents": "الوثائق المطلوبة",
    },
    "fr": {
        "onboarding_welcome": "Quel est votre objectif d'immigration ?",
        "onboarding_welcome_sub": "Nous personnaliserons le reste de l'expérience selon votre objectif. Vos réponses restent privées.",
        "onboarding_destination": "Où allez-vous ?",
        "onboarding_destination_sub": "Choisissez votre pays de destination.",
        "onboarding_visa_recommendations": "Types de visa recommandés",
        "onboarding_visa_recommendations_sub": "Selon votre objectif et destination, voici ce qui convient.",
        "onboarding_eligibility": "Vérification d'éligibilité",
        "onboarding_eligibility_sub": "Questions rapides oui/non sur votre type de visa. Nous identifierons immédiatement tout blocage.",
        "onboarding_strength": "La force de votre dossier",
        "onboarding_strength_sub": "Selon vos réponses, voici votre situation. C'est de l'IA basée sur des règles — chaque facteur est explicable.",
        "onboarding_documents": "Votre liste de documents personnalisée",
        "onboarding_documents_sub": "Selon vos réponses, vous aurez besoin de ces documents spécifiques.",
        "onboarding_attorneys": "Avocats vérifiés prêts à vous aider",
        "onboarding_attorneys_sub": "Nous vous avons mis en relation avec des avocats dont la spécialisation, juridiction et capacité correspondent à votre dossier.",
        "goal_student": "Étudiant",
        "goal_student_desc": "Étudier dans une université, collège ou école de langues",
        "goal_work": "Travail",
        "goal_work_desc": "Emploi, transfert ou profession spécialisée",
        "goal_family": "Famille / Conjoint",
        "goal_family_desc": "Rejoindre la famille ou se marier à l'étranger",
        "goal_pr": "Résidence Permanente",
        "goal_pr_desc": "Green Card, ILR, PR, voie vers la citoyenneté",
        "goal_investor": "Investisseur / Entrepreneur",
        "goal_investor_desc": "Créer une entreprise ou investir à l'étranger",
        "btn_continue": "Continuer →",
        "btn_back": "← Retour",
        "btn_yes": "Oui",
        "btn_no": "Non",
        "btn_submit": "Soumettre",
        "btn_save": "Enregistrer",
        "btn_cancel": "Annuler",
        "btn_open_uploader": "Ouvrir le téléchargeur →",
        "btn_save_continue": "Enregistrer et continuer vers le tableau de bord →",
        "label_required": "*",
        "label_step_of": "Étape {current} sur {total}",
        "compliance_banner": "Verom est une plateforme technologique — nous organisons les informations et vous aidons à vous connecter avec des avocats vérifiés. Verom ne fournit pas de conseils juridiques. Vos données sont chiffrées et ne sont jamais partagées sans votre consentement.",
        "status_intake": "Admission",
        "status_documents": "Documents",
        "status_review": "Révision",
        "status_filed": "Déposé",
        "status_rfe": "RFE",
        "status_approved": "Approuvé",
        "status_denied": "Refusé",
        "tier_excellent": "EXCELLENT",
        "tier_strong": "FORT",
        "tier_moderate": "MODÉRÉ",
        "tier_weak": "FAIBLE",
        "docs_completeness": "Complétude",
        "docs_no_uploads": "Aucun document téléchargé pour le moment",
        "docs_drop_here": "Déposez les fichiers ici ou cliquez pour télécharger",
        "docs_required_documents": "Documents requis",
    },
    "pt": {
        "onboarding_welcome": "Qual é o seu objetivo de imigração?",
        "onboarding_welcome_sub": "Personalizaremos o restante da experiência com base no seu objetivo. Suas respostas são privadas.",
        "onboarding_destination": "Para onde você está indo?",
        "onboarding_destination_sub": "Escolha o seu país de destino.",
        "onboarding_visa_recommendations": "Tipos de visto recomendados",
        "onboarding_visa_recommendations_sub": "Com base no seu objetivo e destino, aqui está o que se encaixa.",
        "onboarding_eligibility": "Verificação de elegibilidade",
        "onboarding_eligibility_sub": "Perguntas rápidas de sim/não sobre seu tipo de visto. Identificaremos qualquer bloqueio imediatamente.",
        "onboarding_strength": "A força do seu caso",
        "onboarding_strength_sub": "Com base nas suas respostas, esta é sua situação. É IA baseada em regras — cada fator é explicável.",
        "onboarding_documents": "Sua lista personalizada de documentos",
        "onboarding_documents_sub": "Com base nas suas respostas, você precisará destes documentos específicos.",
        "onboarding_attorneys": "Advogados verificados prontos para ajudar",
        "onboarding_attorneys_sub": "Combinamos você com advogados cuja especialização, jurisdição e capacidade se ajustam ao seu caso.",
        "goal_student": "Estudante",
        "goal_student_desc": "Estudar em universidade, faculdade ou escola de idiomas",
        "goal_work": "Trabalho",
        "goal_work_desc": "Emprego, transferência ou ocupação especializada",
        "goal_family": "Família / Cônjuge",
        "goal_family_desc": "Reunir-se com a família ou casar-se no exterior",
        "goal_pr": "Residência Permanente",
        "goal_pr_desc": "Green Card, ILR, PR, caminho para cidadania",
        "goal_investor": "Investidor / Empreendedor",
        "goal_investor_desc": "Construir um negócio ou investir no exterior",
        "btn_continue": "Continuar →",
        "btn_back": "← Voltar",
        "btn_yes": "Sim",
        "btn_no": "Não",
        "btn_submit": "Enviar",
        "btn_save": "Salvar",
        "btn_cancel": "Cancelar",
        "btn_open_uploader": "Abrir uploader →",
        "btn_save_continue": "Salvar e continuar para o painel →",
        "label_required": "*",
        "label_step_of": "Etapa {current} de {total}",
        "compliance_banner": "Verom é uma plataforma tecnológica — organizamos informações e ajudamos você a se conectar com advogados verificados. Verom não fornece aconselhamento jurídico. Seus dados são criptografados e nunca compartilhados sem seu consentimento.",
        "status_intake": "Admissão",
        "status_documents": "Documentos",
        "status_review": "Revisão",
        "status_filed": "Apresentado",
        "status_rfe": "RFE",
        "status_approved": "Aprovado",
        "status_denied": "Negado",
        "tier_excellent": "EXCELENTE",
        "tier_strong": "FORTE",
        "tier_moderate": "MODERADO",
        "tier_weak": "FRACO",
        "docs_completeness": "Completude",
        "docs_no_uploads": "Nenhum documento carregado ainda",
        "docs_drop_here": "Solte os arquivos aqui ou clique para enviar",
        "docs_required_documents": "Documentos obrigatórios",
    },
}


# ---------------------------------------------------------------------------
# Disclaimer text per language
# ---------------------------------------------------------------------------

TRANSLATION_DISCLAIMERS: dict[str, str] = {
    "en": "(AI-assisted translation. The English version is the legal record.)",
    "zh": "(AI 辅助翻译。英文版本为法律记录。)",
    "es": "(Traducción asistida por IA. La versión en inglés es el registro legal.)",
    "hi": "(AI-सहायक अनुवाद। अंग्रेजी संस्करण कानूनी रिकॉर्ड है।)",
    "ar": "(ترجمة بمساعدة الذكاء الاصطناعي. النسخة الإنجليزية هي السجل القانوني.)",
    "fr": "(Traduction assistée par IA. La version anglaise est le document légal.)",
    "pt": "(Tradução assistida por IA. A versão em inglês é o registro legal.)",
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TranslationService:
    """Multi-language UI dictionary + ad-hoc message translation."""

    def __init__(self, llm_translator: Any | None = None) -> None:
        # llm_translator: optional callable(text, source_lang, target_lang) → str
        # If None, uses a deterministic mock for tests/dev
        self._llm = llm_translator
        self._cache: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_supported_languages() -> list[dict]:
        return [
            {"code": code, "name": LANGUAGE_NAMES.get(code, code), "rtl": code in RTL_LANGUAGES}
            for code in SUPPORTED_LANGUAGES
        ]

    @staticmethod
    def list_ui_keys() -> list[str]:
        return sorted(UI_STRINGS["en"].keys())

    # ---------- UI dictionary ----------
    @staticmethod
    def get_ui_strings(lang: str) -> dict[str, str]:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return dict(UI_STRINGS.get(lang, UI_STRINGS["en"]))

    @staticmethod
    def get_ui_string(key: str, lang: str = "en") -> str:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return UI_STRINGS.get(lang, UI_STRINGS["en"]).get(key, UI_STRINGS["en"].get(key, key))

    # ---------- ad-hoc translation ----------
    def translate_message(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "en",
        include_disclaimer: bool = True,
    ) -> dict:
        if source_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported source language: {source_lang}")
        if target_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported target language: {target_lang}")
        if not text or not text.strip():
            raise ValueError("Empty text")

        cache_key = f"{source_lang}:{target_lang}:{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if source_lang == target_lang:
            translated = text
        elif self._llm is not None:
            try:
                translated = self._llm(text, source_lang, target_lang)
            except Exception:
                translated = self._mock_translate(text, source_lang, target_lang)
        else:
            translated = self._mock_translate(text, source_lang, target_lang)

        result = {
            "id": str(uuid.uuid4()),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "original_text": text,
            "translated_text": translated,
            "disclaimer": TRANSLATION_DISCLAIMERS.get(target_lang, TRANSLATION_DISCLAIMERS["en"]) if include_disclaimer else None,
            "is_mock": self._llm is None,
            "translated_at": datetime.utcnow().isoformat(),
        }
        self._cache[cache_key] = result
        return result

    def translate_attorney_to_client(
        self, attorney_message: str, client_language: str = "en",
    ) -> dict:
        """Convenience: translate from English (legal record) to client language.
        Always returns a payload with both versions side by side."""
        return self.translate_message(
            text=attorney_message, source_lang="en", target_lang=client_language,
            include_disclaimer=True,
        )

    def translate_client_to_attorney(
        self, client_message: str, client_language: str = "en",
    ) -> dict:
        """Translate client's reply into English so the attorney can read it.
        The English translation does NOT replace the original — the original
        remains the source of truth in case the attorney needs to review it."""
        return self.translate_message(
            text=client_message, source_lang=client_language, target_lang="en",
            include_disclaimer=True,
        )

    @staticmethod
    def _mock_translate(text: str, source: str, target: str) -> str:
        """Deterministic mock that prefixes the text. Real implementation
        swaps in a provider — DeepL, Google Translate, Anthropic, etc."""
        return f"[{source}→{target}] {text}"

    # ---------- introspection ----------
    @staticmethod
    def list_disclaimers() -> dict[str, str]:
        return dict(TRANSLATION_DISCLAIMERS)
