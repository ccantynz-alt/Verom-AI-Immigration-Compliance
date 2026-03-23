/**
 * Verom.ai — Lightweight i18n for applicant-facing pages.
 * Attorney portal and legal content stay in English per language strategy.
 */
(function() {
    'use strict';

    var translations = {
        zh: {
            nav_login: '登录',
            nav_cta: '免费开始',
            hero_badge: 'AI 驱动的移民平台',
            hero_title_1: '移民合规，',
            hero_title_2: '妥善处理。',
            hero_sub: '无论您是申请学生签证、工作许可还是家庭团聚——Verom 将您与持牌移民律师和 AI 合规工具连接，让您自信地完成整个流程。',
            hero_cta_primary: '开始您的申请',
            hero_cta_secondary: '以律师身份加入 →',
            stat_countries: '目的地国家',
            stat_engine: '合规引擎',
            stat_matching: '律师匹配',
            stat_visas: '学生、工作、家庭等',
            problem_title: '移民不该像赌博一样。',
            applicant_title: '为出发的人准备。',
            applicant_sub: 'AI 引导的签证申请，配有真正的律师支持——面向学生、工作者和家庭。',
            cta_final_title: '您的未来不应该取决于文书工作。',
            cta_final_sub: '加入申请人和律师，共同打造更好的移民体验。',
            footer_disclaimer: '© 2026 Verom.ai。保留所有权利。Verom 是一个技术平台，不提供法律建议。律师费用由每位律师独立设定，Verom 不决定也不保证收费标准。',
        },
        es: {
            nav_login: 'Iniciar sesión',
            nav_cta: 'Comienza gratis',
            hero_badge: 'Plataforma de inmigración con IA',
            hero_title_1: 'Cumplimiento migratorio,',
            hero_title_2: 'bien hecho.',
            hero_sub: 'Ya sea que solicites una visa de estudiante, permiso de trabajo o reunificación familiar — Verom te conecta con abogados de inmigración licenciados y herramientas de cumplimiento con IA.',
            hero_cta_primary: 'Comienza tu solicitud',
            hero_cta_secondary: 'Únete como abogado →',
            stat_countries: 'Países de destino',
            stat_engine: 'Motor de cumplimiento',
            stat_matching: 'Emparejamiento de abogados',
            stat_visas: 'Estudiante, trabajo, familia y más',
            problem_title: 'La inmigración no debería ser una apuesta.',
            applicant_title: 'Para personas que van a lugares.',
            applicant_sub: 'Solicitudes de visa guiadas por IA con apoyo real de abogados — para estudiantes, trabajadores y familias.',
            cta_final_title: 'Tu futuro no debería depender del papeleo.',
            cta_final_sub: 'Únete a solicitantes y abogados construyendo una mejor experiencia migratoria.',
            footer_disclaimer: '© 2026 Verom.ai. Todos los derechos reservados. Verom es una plataforma tecnológica y no proporciona asesoramiento legal. Los honorarios de los abogados son establecidos independientemente por cada abogado y no son determinados ni garantizados por Verom.',
        },
        hi: {
            nav_login: 'लॉग इन',
            nav_cta: 'मुफ्त शुरू करें',
            hero_badge: 'AI-संचालित इमिग्रेशन प्लेटफॉर्म',
            hero_title_1: 'इमिग्रेशन अनुपालन,',
            hero_title_2: 'सही तरीके से।',
            hero_sub: 'चाहे आप स्टूडेंट वीज़ा, वर्क परमिट या फैमिली रीयूनिफिकेशन के लिए आवेदन कर रहे हों — Verom आपको लाइसेंस प्राप्त इमिग्रेशन वकीलों और AI अनुपालन टूल से जोड़ता है।',
            hero_cta_primary: 'अपना आवेदन शुरू करें',
            hero_cta_secondary: 'वकील के रूप में जुड़ें →',
            stat_countries: 'गंतव्य देश',
            stat_engine: 'अनुपालन इंजन',
            stat_matching: 'वकील मिलान',
            stat_visas: 'छात्र, कार्य, परिवार और अधिक',
            problem_title: 'इमिग्रेशन जुआ जैसा नहीं होना चाहिए।',
            applicant_title: 'आगे बढ़ने वालों के लिए।',
            applicant_sub: 'AI-निर्देशित वीज़ा आवेदन वास्तविक वकील सहायता के साथ — छात्रों, कामगारों और परिवारों के लिए।',
            cta_final_title: 'आपका भविष्य कागजी कार्रवाई पर निर्भर नहीं होना चाहिए।',
            cta_final_sub: 'बेहतर इमिग्रेशन अनुभव बनाने वाले आवेदकों और वकीलों से जुड़ें।',
            footer_disclaimer: '© 2026 Verom.ai। सर्वाधिकार सुरक्षित। Verom एक प्रौद्योगिकी मंच है और कानूनी सलाह प्रदान नहीं करता। वकील शुल्क प्रत्येक वकील द्वारा स्वतंत्र रूप से निर्धारित किए जाते हैं।',
        },
        ar: {
            nav_login: 'تسجيل الدخول',
            nav_cta: 'ابدأ مجاناً',
            hero_badge: 'منصة هجرة مدعومة بالذكاء الاصطناعي',
            hero_title_1: 'الامتثال للهجرة،',
            hero_title_2: 'بالشكل الصحيح.',
            hero_sub: 'سواء كنت تتقدم للحصول على تأشيرة طالب أو تصريح عمل أو لم شمل الأسرة — يربطك Verom بمحامي هجرة مرخصين وأدوات امتثال مدعومة بالذكاء الاصطناعي.',
            hero_cta_primary: 'ابدأ طلبك',
            hero_cta_secondary: 'انضم كمحامٍ ←',
            stat_countries: 'دول الوجهة',
            stat_engine: 'محرك الامتثال',
            stat_matching: 'مطابقة المحامين',
            stat_visas: 'طالب، عمل، عائلة والمزيد',
            problem_title: 'الهجرة لا ينبغي أن تكون مقامرة.',
            applicant_title: 'لمن يتطلعون للمستقبل.',
            applicant_sub: 'طلبات تأشيرة موجهة بالذكاء الاصطناعي مع دعم حقيقي من المحامين — للطلاب والعمال والعائلات.',
            cta_final_title: 'مستقبلك لا يجب أن يعتمد على الأوراق.',
            cta_final_sub: 'انضم إلى المتقدمين والمحامين لبناء تجربة هجرة أفضل.',
            footer_disclaimer: '© 2026 Verom.ai. جميع الحقوق محفوظة. Verom هي منصة تقنية ولا تقدم استشارات قانونية. يتم تحديد رسوم المحامين بشكل مستقل من قبل كل محامٍ.',
        },
        fr: {
            nav_login: 'Connexion',
            nav_cta: 'Commencer gratuitement',
            hero_badge: "Plateforme d'immigration IA",
            hero_title_1: "Conformité d'immigration,",
            hero_title_2: 'bien gérée.',
            hero_sub: "Que vous postuliez pour un visa étudiant, un permis de travail ou un regroupement familial — Verom vous connecte avec des avocats d'immigration agréés et des outils de conformité IA.",
            hero_cta_primary: 'Commencer votre demande',
            hero_cta_secondary: "Rejoindre en tant qu'avocat →",
            stat_countries: 'Pays de destination',
            stat_engine: 'Moteur de conformité',
            stat_matching: 'Mise en relation avocats',
            stat_visas: 'Étudiant, travail, famille et plus',
            problem_title: "L'immigration ne devrait pas être un pari.",
            applicant_title: 'Pour ceux qui vont de l\'avant.',
            applicant_sub: "Demandes de visa guidées par l'IA avec un véritable soutien d'avocats — pour étudiants, travailleurs et familles.",
            cta_final_title: 'Votre avenir ne devrait pas dépendre de la paperasse.',
            cta_final_sub: "Rejoignez les candidats et avocats qui construisent une meilleure expérience d'immigration.",
            footer_disclaimer: "© 2026 Verom.ai. Tous droits réservés. Verom est une plateforme technologique et ne fournit pas de conseils juridiques. Les honoraires des avocats sont fixés indépendamment par chaque avocat.",
        },
        pt: {
            nav_login: 'Entrar',
            nav_cta: 'Comece grátis',
            hero_badge: 'Plataforma de imigração com IA',
            hero_title_1: 'Conformidade migratória,',
            hero_title_2: 'bem feita.',
            hero_sub: 'Seja para visto de estudante, permissão de trabalho ou reunificação familiar — Verom conecta você com advogados de imigração licenciados e ferramentas de conformidade com IA.',
            hero_cta_primary: 'Comece sua aplicação',
            hero_cta_secondary: 'Junte-se como advogado →',
            stat_countries: 'Países de destino',
            stat_engine: 'Motor de conformidade',
            stat_matching: 'Correspondência de advogados',
            stat_visas: 'Estudante, trabalho, família e mais',
            problem_title: 'Imigração não deveria ser uma aposta.',
            applicant_title: 'Para pessoas que vão a lugares.',
            applicant_sub: 'Aplicações de visto guiadas por IA com suporte real de advogados — para estudantes, trabalhadores e famílias.',
            cta_final_title: 'Seu futuro não deveria depender de burocracia.',
            cta_final_sub: 'Junte-se a candidatos e advogados construindo uma melhor experiência de imigração.',
            footer_disclaimer: '© 2026 Verom.ai. Todos os direitos reservados. Verom é uma plataforma tecnológica e não fornece aconselhamento jurídico. Os honorários dos advogados são definidos independentemente por cada advogado.',
        },
    };

    // Map of data-i18n keys to their English defaults (captured on first load)
    var englishDefaults = {};

    function applyLanguage(lang) {
        var dict = translations[lang];
        document.querySelectorAll('[data-i18n]').forEach(function(el) {
            var key = el.getAttribute('data-i18n');
            // Capture English default on first run
            if (!englishDefaults[key]) {
                englishDefaults[key] = el.innerHTML;
            }
            if (dict && dict[key]) {
                el.innerHTML = dict[key];
            } else {
                el.innerHTML = englishDefaults[key];
            }
        });
        // Set dir for RTL languages
        document.documentElement.dir = (lang === 'ar') ? 'rtl' : 'ltr';
        localStorage.setItem('verom_lang', lang);
    }

    // Initialize
    var saved = localStorage.getItem('verom_lang') || 'en';
    var select = document.getElementById('langSelect');
    if (select) {
        select.value = saved;
        if (saved !== 'en') applyLanguage(saved);
        select.addEventListener('change', function() {
            applyLanguage(this.value);
        });
    }
})();
