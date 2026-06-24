BEGIN;

-- 002: Modul toggle modeli.
-- Ilgari asosiy modullar (tz_pr_checker, testcase_generator) `get_effective_company_modules`
-- ichidagi plan-forcing orqali majburan yoqilardi. Endi `enabled_modules` yagona manba:
-- super-admin har modulni alohida yoqib-o'chira oladi. Mavjud kompaniyalarning
-- amaldagi (yoqiq) holatini saqlab qolish uchun asosiy modullarni explicit true qilamiz.
UPDATE company_settings
SET enabled_modules = (
        COALESCE(NULLIF(enabled_modules, '')::jsonb, '{}'::jsonb)
        || '{"tz_pr_checker": true, "testcase_generator": true}'::jsonb
    )::text,
    updated_at = NOW();

COMMIT;
