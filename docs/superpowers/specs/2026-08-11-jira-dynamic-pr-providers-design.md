# JIRA Dynamic PR Providers Design

## Muammo

JIRA Development Status summary taskdagi PR providerini
`oAuth-com.github.integration.production` deb qaytaradi. `JiraClient` esa detail
endpointni faqat `applicationType=GitHub` bilan chaqirgani sabab DEV-8843 uchun
PR #11745 servisga yetib kelmagan.

## Yechim

`extract_pr_urls_dev_status()` avval JIRA development summary endpointidan
`pullrequest.byInstanceType` kalitlarini oladi. Har bir qaytgan provider uchun
detail endpoint chaqiriladi, barcha detail bloklaridagi GitHub PR URLlari
yig'iladi va URL bo'yicha takrorlar olib tashlanadi.

Summary endpoint ishlamasa yoki provider qaytarmasa, backward compatibility
uchun eski `GitHub` provideriga fallback qilinadi. Bitta provider xatosi qolgan
providerlarni tekshirishga to'sqinlik qilmaydi.

## Scope

- Backend: `utils/jira/jira_client.py`
- Regression tests: `tests/test_jira_client.py`
- Webhook, UI va worker bir xil `JiraClient` oqimidan foydalangani sabab alohida
  engine fork yaratilmaydi.
- DB, sozlama, frontend va multi-agent JSON kontrakti o'zgarmaydi.

## Tekshiruv

- OAuth provider discovery va PR extraction regressiya testi.
- Bir PR bir nechta provider orqali kelsa URL dedupe testi.
- Production deploydan keyin DEV-8843 uchun `pr_urls` ichida PR #11745 borligi
  read-only probe bilan tekshiriladi.

