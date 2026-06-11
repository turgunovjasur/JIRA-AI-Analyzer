DEV-8144


Error - Zakaz da product o'chib ketish xatoligi



Key details
Description

Zakaz da Product tanlangandan so’ng, bir hil turdagi contract larni almashtirilsa, garcha Valyutasi, Price_type bir xil bolsa ham tanlangan Product lar ochib ketyapti

--------

{
  "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
  "task_key": "DEV-8144",
  "company_id": 329,
  "user_id": 160,
  "source": "manual",
  "execution_mode": "multi_agent",
  "run_state": "blocked",
  "active_phase": "finished",
  "status_message": "Run manual review yoki block holatida tugadi",
  "requested_output_profile": "ui",
  "error_message": "",
  "created_at": "2026-05-22T18:32:54.097172+05:00",
  "updated_at": "2026-05-22T18:36:00.720846+05:00",
  "started_at": "2026-05-22T18:32:54.112285+05:00",
  "finished_at": "2026-05-22T18:36:00.720842+05:00",
  "request_payload": {
    "task_key": "DEV-8144",
    "output_profile": "ui",
    "show_full_diff": true,
    "use_smart_patch": null,
    "max_files": null,
    "execution_mode": "multi_agent"
  },
  "final_result": {
    "task_key": "DEV-8144",
    "task_summary": "Error - Zakaz da product o'chib ketish xatoligi",
    "tz_content": "📋 SUMMARY:\nError - Zakaz da product o'chib ketish xatoligi\n\n📝 DESCRIPTION (TZ):\nZakaz da Product tanlangandan so’ng, bir hil turdagi contract larni almashtirilsa, garcha Valyutasi, Price_type bir xil bolsa ham tanlangan Product lar ochib ketyapti\n\n!image-20260409-113105.png|width=686,alt=\"image-20260409-113105.png\"!\n\ncontrakt-1\n\n!image-20260409-113518.png|width=686,alt=\"image-20260409-113518.png\"!\n\ncontrakt-2\n\n!image-20260409-113553.png|width=686,alt=\"image-20260409-113553.png\"!\n\n📊 METADATA:\n   Type: DEV-ERROR\n   Priority: Medium\n   Status: Closed\n   Assignee: Nekboyev og'abek\n   Reporter: Turgunov Jasur\n   Created: 2026-04-09\n   Story Points: 1.0\n   Labels: Order_form",
    "pr_count": 1,
    "files_changed": 4,
    "total_additions": 45,
    "total_deletions": 46,
    "pr_details": [
      {
        "url": "https://github.com/greenwhite/smartup5x_anor/pull/11382",
        "owner": "greenwhite",
        "repo": "smartup5x_anor",
        "number": 11382,
        "title": "Fix: contract change false price type mismatch warning in order form",
        "state": "closed",
        "merged": true,
        "additions": 45,
        "deletions": 46,
        "files_count": 4,
        "files": [
          {
            "filename": "main/oracle/ui/anor/mdeal/order/order/order.pkb",
            "status": "modified",
            "additions": 12,
            "deletions": 20,
            "changes": 32,
            "patch": "@@ -459,13 +459,10 @@ create or replace package body Ui_Anor279 is\n \n     q := Fazo_Query('select t.*,\n                             k.name payment_type_name,\n-                            case\n-                                  when exists (select 1\n-                                          from mkf_contract_price_types w\n-                                         where w.company_id = t.company_id\n-                                           and w.contract_id = t.contract_id)\n-                            then ''Y''\n-                            else ''N'' end has_price_type\n+                            (select listagg(w.price_type_id, '','') within group (order by w.price_type_id)\n+                               from mkf_contract_price_types w\n+                              where w.company_id = t.company_id\n+                                and w.contract_id = t.contract_id) contract_price_type_ids\n                        from mkf_contracts t\n                        left join mkr_payment_types k\n                          on k.company_id = t.company_id\n@@ -484,7 +481,7 @@ create or replace package body Ui_Anor279 is\n                    'consignment_day_limit',\n                    'deal_booked_payment_min_percent',\n                    'payment_type_id');\n-    q.Varchar2_Field('name', 'allow_auto_consignment', 'has_price_type', 'payment_type_name');\n+    q.Varchar2_Field('name', 'allow_auto_consignment', 'contract_price_type_ids', 'payment_type_name');\n \n     q.Refer_Field('currency_name', 'currency_id', 'mk_currencies', 'currency_id', 'name');\n     return q;\n@@ -3182,7 +3179,7 @@ create or replace package body Ui_Anor279 is\n     v_Result_Consignment_Day_Limit           number;\n     v_Result_Allow_Auto_Consignment          varchar(2);\n     v_Result_Deal_Booked_Payment_Min_Percent number;\n-    v_Has_Price_Type                         varchar2(1);\n+    v_Contract_Price_Type_Ids               varchar2(4000);\n     v_Result_Payment_Type_Id                 number;\n     v_Result_Payment_Type_Name               varchar2(200);\n \n@@ -3208,15 +3205,10 @@ create or replace package body Ui_Anor279 is\n                 from Mkr_Payment_Types t\n                where t.Company_Id = k.Company_Id\n                  and t.Payment_Type_Id = k.Payment_Type_Id) Payment_Type_Name,\n-             case\n-               when exists (select 1\n-                       from Mkf_Contract_Price_Types w\n-                      where w.Company_Id = k.Company_Id\n-                        and w.Contract_Id = k.Contract_Id) then\n-                'Y'\n-               else\n-                'N'\n-             end\n+             (select listagg(w.Price_Type_Id, ',') within group(order by w.Price_Type_Id)\n+                from Mkf_Contract_Price_Types w\n+               where w.Company_Id = k.Company_Id\n+                 and w.Contract_Id = k.Contract_Id) Contract_Price_Type_Ids\n         into v_Result_Contract_Id,\n              v_Result_Contract_Name,\n              v_Result_Subfilial_Id,\n@@ -3226,7 +3218,7 @@ create or replace package body Ui_Anor279 is\n              v_Result_Deal_Booked_Payment_Min_Percent,\n              v_Result_Payment_Type_Id,\n              v_Result_Payment_Type_Name,\n-             v_Has_Price_Type\n+             v_Contract_Price_Type_Ids\n         from Mkf_Contracts k\n        where k.Company_Id = v_Company_Id\n          and k.Filial_Id = v_Filial_Id\n@@ -3252,7 +3244,7 @@ create or replace package body Ui_Anor279 is\n     Result.Put('deal_booked_payment_min_percent', v_Result_Deal_Booked_Payment_Min_Percent);\n     Result.Put('payment_type_id', v_Result_Payment_Type_Id);\n     Result.Put('payment_type_name', v_Result_Payment_Type_Name);\n-    Result.Put('has_price_type', v_Has_Price_Type);\n+    Result.Put('contract_price_type_ids', v_Contract_Price_Type_Ids);\n \n     return result;\n   end;",
            "blob_url": "https://github.com/greenwhite/smartup5x_anor/blob/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Foracle%2Fui%2Fanor%2Fmdeal%2Forder%2Forder%2Forder.pkb",
            "raw_url": "https://github.com/greenwhite/smartup5x_anor/raw/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Foracle%2Fui%2Fanor%2Fmdeal%2Forder%2Forder%2Forder.pkb",
            "contents_url": "https://api.github.com/repos/greenwhite/smartup5x_anor/contents/main%2Foracle%2Fui%2Fanor%2Fmdeal%2Forder%2Forder%2Forder.pkb?ref=ec3786dd15a1ab7d6884e5bfd60668af95b52d1d",
            "sha": "6261224d92af56aec787625bd1496fe2f46d6363",
            "previous_filename": "",
            "smart_context": null
          },
          {
            "filename": "main/oracle/ui/anor/mdeal/order/order_beta/order_beta.pkb",
            "status": "modified",
            "additions": 13,
            "deletions": 20,
            "changes": 33,
            "patch": "@@ -50,13 +50,10 @@ create or replace package body Ui_Anor1446 is\n \n     q := Fazo_Query('select t.*,\n                             k.name payment_type_name,\n-                             case\n-                                  when exists (select 1\n-                                          from mkf_contract_price_types w\n-                                         where w.company_id = t.company_id\n-                                           and w.contract_id = t.contract_id)\n-                             then ''Y''\n-                             else ''N'' end has_price_type\n+                            (select listagg(w.price_type_id, '','') within group (order by w.price_type_id)\n+                               from mkf_contract_price_types w\n+                              where w.company_id = t.company_id\n+                                and w.contract_id = t.contract_id) contract_price_type_ids\n                        from mkf_contracts t\n                        left join mkr_payment_types k\n                          on k.company_id = t.company_id\n@@ -75,7 +72,8 @@ create or replace package body Ui_Anor1446 is\n                    'consignment_day_limit',\n                    'deal_booked_payment_min_percent',\n                    'payment_type_id');\n-    q.Varchar2_Field('name', 'allow_auto_consignment', 'has_price_type', 'payment_type_name');\n+    q.Varchar2_Field('name', 'allow_auto_consignment', 'contract_price_type_ids', 'payment_type_name');\n+\n \n     q.Refer_Field('currency_name', 'currency_id', 'mk_currencies', 'currency_id', 'name');\n     return q;\n@@ -3557,7 +3555,7 @@ create or replace package body Ui_Anor1446 is\n     v_Result_Consignment_Day_Limit           number;\n     v_Result_Allow_Auto_Consignment          varchar(2);\n     v_Result_Deal_Booked_Payment_Min_Percent number;\n-    v_Has_Price_Type                         varchar2(1);\n+    v_Contract_Price_Type_Ids               varchar2(4000);\n     v_Result_Payment_Type_Id                 number;\n     v_Result_Payment_Type_Name               varchar2(200);\n \n@@ -3583,15 +3581,10 @@ create or replace package body Ui_Anor1446 is\n                 from Mkr_Payment_Types t\n                where t.Company_Id = k.Company_Id\n                  and t.Payment_Type_Id = k.Payment_Type_Id) Payment_Type_Name,\n-             case\n-               when exists (select 1\n-                       from Mkf_Contract_Price_Types w\n-                      where w.Company_Id = k.Company_Id\n-                        and w.Contract_Id = k.Contract_Id) then\n-                'Y'\n-               else\n-                'N'\n-             end\n+             (select listagg(w.Price_Type_Id, ',') within group(order by w.Price_Type_Id)\n+                from Mkf_Contract_Price_Types w\n+               where w.Company_Id = k.Company_Id\n+                 and w.Contract_Id = k.Contract_Id) Contract_Price_Type_Ids\n         into v_Result_Contract_Id,\n              v_Result_Contract_Name,\n              v_Result_Subfilial_Id,\n@@ -3601,7 +3594,7 @@ create or replace package body Ui_Anor1446 is\n              v_Result_Deal_Booked_Payment_Min_Percent,\n              v_Result_Payment_Type_Id,\n              v_Result_Payment_Type_Name,\n-             v_Has_Price_Type\n+             v_Contract_Price_Type_Ids\n         from Mkf_Contracts k\n        where k.Company_Id = v_Company_Id\n          and k.Filial_Id = v_Filial_Id\n@@ -3626,7 +3619,7 @@ create or replace package body Ui_Anor1446 is\n     Result.Put('deal_booked_payment_min_percent', v_Result_Deal_Booked_Payment_Min_Percent);\n     Result.Put('payment_type_id', v_Result_Payment_Type_Id);\n     Result.Put('payment_type_name', v_Result_Payment_Type_Name);\n-    Result.Put('has_price_type', v_Has_Price_Type);\n+    Result.Put('contract_price_type_ids', v_Contract_Price_Type_Ids);\n \n     return result;\n   end;",
            "blob_url": "https://github.com/greenwhite/smartup5x_anor/blob/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Foracle%2Fui%2Fanor%2Fmdeal%2Forder%2Forder_beta%2Forder_beta.pkb",
            "raw_url": "https://github.com/greenwhite/smartup5x_anor/raw/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Foracle%2Fui%2Fanor%2Fmdeal%2Forder%2Forder_beta%2Forder_beta.pkb",
            "contents_url": "https://api.github.com/repos/greenwhite/smartup5x_anor/contents/main%2Foracle%2Fui%2Fanor%2Fmdeal%2Forder%2Forder_beta%2Forder_beta.pkb?ref=ec3786dd15a1ab7d6884e5bfd60668af95b52d1d",
            "sha": "9701d692dbdba6f9425a8b2a7547ecfe2ae88dbf",
            "previous_filename": "",
            "smart_context": null
          },
          {
            "filename": "main/page/form/anor/mdeal/order/order.html",
            "status": "modified",
            "additions": 10,
            "deletions": 3,
            "changes": 13,
            "patch": "@@ -958,6 +958,13 @@\n     }).length;\n   }\n \n+  function hasPriceTypeMismatch(contractPriceTypeIds) {\n+    if (!contractPriceTypeIds) return false;\n+    var allowed = _.map(contractPriceTypeIds.split(','), Number);\n+    var usedIds = _.filter(_.map(priceTypeIds(), Number), function(id) { return !!id; });\n+    return _.some(usedIds, function(id) { return !_.contains(allowed, id); });\n+  }\n+\n   function clearListAll() {\n     _.each(_.union(ctrl.inventories, ctrl.exchange_inventories, [ctrl.service]), function(obj) {\n       ctrl.products = obj;\n@@ -1347,7 +1354,7 @@\n           changeMinConsignmentDate();\n \n           changeMinConsignmentDate();\n-          if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+          if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n             page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n               clearListAll();\n \n@@ -1385,7 +1392,7 @@\n       }\n       changeMinConsignmentDate();\n \n-      if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+      if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n         page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n           clearListAll();\n \n@@ -4098,7 +4105,7 @@ <h3 class=\"wizard-title\"><t>finishing</t></h3>\n                     <b-input name=\"contracts\"\n                               model=\"d.contract_name\"\n                               model-key=\"d.contract_id\"\n-                              column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, has_price_type, payment_type_id, payment_type_name\"\n+                              column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, contract_price_type_ids, payment_type_id, payment_type_name\"\n                               search=\"name\"\n                               on-select=\"setContract(row)\"\n                               on-delete=\"deleteContract()\"",
            "blob_url": "https://github.com/greenwhite/smartup5x_anor/blob/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Fpage%2Fform%2Fanor%2Fmdeal%2Forder%2Forder.html",
            "raw_url": "https://github.com/greenwhite/smartup5x_anor/raw/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Fpage%2Fform%2Fanor%2Fmdeal%2Forder%2Forder.html",
            "contents_url": "https://api.github.com/repos/greenwhite/smartup5x_anor/contents/main%2Fpage%2Fform%2Fanor%2Fmdeal%2Forder%2Forder.html?ref=ec3786dd15a1ab7d6884e5bfd60668af95b52d1d",
            "sha": "e5d725a00ef36bf951d405f61a1a5796a29fc10a",
            "previous_filename": "",
            "smart_context": "**📦 Affected Functions:**\n- `clearListAll` (line 968)\n  ```javascript\n  function clearListAll() {\n  ```\n- `hasPriceTypeMismatch` (line 961)\n  ```javascript\n  function hasPriceTypeMismatch(contractPriceTypeIds) {\n  ```\n\n**Changes:** +10 lines\n```diff\n@@ -958,6 +958,13 @@\n     }).length;\n   }\n \n+  function hasPriceTypeMismatch(contractPriceTypeIds) {\n+    if (!contractPriceTypeIds) return false;\n+    var allowed = _.map(contractPriceTypeIds.split(','), Number);\n+    var usedIds = _.filter(_.map(priceTypeIds(), Number), function(id) { return !!id; });\n+    return _.some(usedIds, function(id) { return !_.contains(allowed, id); });\n+  }\n+\n   function clearListAll() {\n     _.each(_.union(ctrl.inventories, ctrl.exchange_inventories, [ctrl.service]), function(obj) {\n       ctrl.products = obj;\n@@ -1347,7 +1354,7 @@\n           changeMinConsignmentDate();\n \n           changeMinConsignmentDate();\n-          if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+          if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n             page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n               clearListAll();\n \n@@ -1385,7 +1392,7 @@\n       }\n       changeMinConsignmentDate();\n \n-      if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+      if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n         page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n           clearListAll();\n \n@@ -4098,7 +4105,7 @@ <h3 class=\"wizard-title\"><t>finishing</t></h3>\n                     <b-input name=\"contracts\"\n                               model=\"d.contract_name\"\n                               model-key=\"d.contract_id\"\n-                              column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, has_price_type, payment_type_id, payment_type_name\"\n+                              column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, contract_price_type_ids, payment_type_id, payment_type_name\"\n                               search=\"name\"\n                               on-select=\"setContract(row)\"\n                               on-delete=\"deleteContract()\"\n```"
          },
          {
            "filename": "main/page/form/anor/mdeal/order/order_beta.html",
            "status": "modified",
            "additions": 10,
            "deletions": 3,
            "changes": 13,
            "patch": "@@ -984,7 +984,7 @@\n           changeMinConsignmentDate();\n \n           changeMinConsignmentDate();\n-          if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+          if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n             page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n               clearListAll();\n \n@@ -1029,7 +1029,7 @@\n       }\n       changeMinConsignmentDate();\n \n-      if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+      if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n         page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n           clearListAll();\n \n@@ -1783,6 +1783,13 @@\n     tryAddEmptyRow();\n   }\n \n+  function hasPriceTypeMismatch(contractPriceTypeIds) {\n+    if (!contractPriceTypeIds) return false;\n+    var allowed = _.map(contractPriceTypeIds.split(','), Number);\n+    var usedIds = _.filter(_.map(priceTypeIds(), Number), function(id) { return !!id; });\n+    return _.some(usedIds, function(id) { return !_.contains(allowed, id); });\n+  }\n+\n   function clearListAll() {\n     if (ctrl.inventories) { // +\n       ctrl.products = ctrl.inventories;\n@@ -5261,7 +5268,7 @@\n               <b-input name=\"contracts\"\n                         model=\"d.contract_name\"\n                         model-key=\"d.contract_id\"\n-                        column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, has_price_type, payment_type_id, payment_type_name\"\n+                        column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, contract_price_type_ids, payment_type_id, payment_type_name\"\n                         search=\"name\"\n                         on-select=\"setContract(row)\"\n                         on-delete=\"deleteContract()\"",
            "blob_url": "https://github.com/greenwhite/smartup5x_anor/blob/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Fpage%2Fform%2Fanor%2Fmdeal%2Forder%2Forder_beta.html",
            "raw_url": "https://github.com/greenwhite/smartup5x_anor/raw/ec3786dd15a1ab7d6884e5bfd60668af95b52d1d/main%2Fpage%2Fform%2Fanor%2Fmdeal%2Forder%2Forder_beta.html",
            "contents_url": "https://api.github.com/repos/greenwhite/smartup5x_anor/contents/main%2Fpage%2Fform%2Fanor%2Fmdeal%2Forder%2Forder_beta.html?ref=ec3786dd15a1ab7d6884e5bfd60668af95b52d1d",
            "sha": "755afcc8a604ba2393711d347f94e9abb6d70ca2",
            "previous_filename": "",
            "smart_context": "**📦 Affected Functions:**\n- `clearListAll` (line 1793)\n  ```javascript\n  function clearListAll() {\n  ```\n- `hasPriceTypeMismatch` (line 1786)\n  ```javascript\n  function hasPriceTypeMismatch(contractPriceTypeIds) {\n  ```\n\n**Changes:** +10 lines\n```diff\n@@ -984,7 +984,7 @@\n           changeMinConsignmentDate();\n \n           changeMinConsignmentDate();\n-          if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+          if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n             page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n               clearListAll();\n \n@@ -1029,7 +1029,7 @@\n       }\n       changeMinConsignmentDate();\n \n-      if (checkHasData() && (ctrl.currency_id != row.currency_id || row.has_price_type == 'Y')) {\n+      if (checkHasData() && (ctrl.currency_id != row.currency_id || hasPriceTypeMismatch(row.contract_price_type_ids))) {\n         page.confirm(t('contract and items currency or price type not equal, all items clear and set contract?')(), function() {\n           clearListAll();\n \n@@ -1783,6 +1783,13 @@\n     tryAddEmptyRow();\n   }\n \n+  function hasPriceTypeMismatch(contractPriceTypeIds) {\n+    if (!contractPriceTypeIds) return false;\n+    var allowed = _.map(contractPriceTypeIds.split(','), Number);\n+    var usedIds = _.filter(_.map(priceTypeIds(), Number), function(id) { return !!id; });\n+    return _.some(usedIds, function(id) { return !_.contains(allowed, id); });\n+  }\n+\n   function clearListAll() {\n     if (ctrl.inventories) { // +\n       ctrl.products = ctrl.inventories;\n@@ -5261,7 +5268,7 @@\n               <b-input name=\"contracts\"\n                         model=\"d.contract_name\"\n                         model-key=\"d.contract_id\"\n-                        column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, has_price_type, payment_type_id, payment_type_name\"\n+                        column=\"contract_id, name, currency_id, currency_name, subfilial_id, consignment_day_limit, allow_auto_consignment, deal_booked_payment_min_percent, contract_price_type_ids, payment_type_id, payment_type_name\"\n                         search=\"name\"\n                         on-select=\"setContract(row)\"\n                         on-delete=\"deleteContract()\"\n```"
          }
        ]
      }
    ],
    "ai_analysis": "## 🧭 XULOSA\nREQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi.\n\n## ✅ BAJARILGAN TALABLAR\n\n## ❌ BAJARILMAGAN TALABLAR\n\n## 🐛 POTENSIAL MUAMMOLAR\n1 ta talab bo'yicha Agent2 verification qaytarmadi; Agent3 contract gap aniqladi (REQ-1).\n- Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}\n\n## 🎨 FIGMA DIZAYN MOSLIGI\nFigma ma'lumotlari olinmadi yoki signal qaytmadi.\n\n## 📊 MOSLIK BALI\n**COMPLIANCE_SCORE: 0%**",
    "compliance_score": 0,
    "success": true,
    "error_message": "",
    "warnings": [
      "Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
    ],
    "status_banner": null,
    "ai_retry_count": 0,
    "files_analyzed": 0,
    "total_prompt_size": 0,
    "figma_data": null,
    "comment_analysis": {
      "has_changes": false,
      "summary": "Comment yo'q",
      "change_count": 0,
      "important_comments": [],
      "filtered_out_ai_comments": 2,
      "total_comments": 0
    },
    "dev_objections": [],
    "analysis_sections": [
      {
        "key": "completed",
        "title": "✅ BAJARILGAN TALABLAR",
        "lines": [],
        "items": [],
        "item_count": 0,
        "empty": true
      },
      {
        "key": "failed",
        "title": "❌ BAJARILMAGAN TALABLAR",
        "lines": [],
        "items": [],
        "item_count": 0,
        "empty": true
      },
      {
        "key": "issues",
        "title": "🐛 POTENSIAL MUAMMOLAR",
        "lines": [
          "1 ta talab bo'yicha Agent2 verification qaytarmadi; Agent3 contract gap aniqladi (REQ-1).",
          "- Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
        ],
        "items": [
          "1 ta talab bo'yicha Agent2 verification qaytarmadi; Agent3 contract gap aniqladi (REQ-1).",
          "- Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
        ],
        "item_count": 2,
        "empty": false
      },
      {
        "key": "figma",
        "title": "🎨 FIGMA DIZAYN MOSLIGI",
        "lines": [],
        "items": [],
        "item_count": 0,
        "empty": true
      }
    ],
    "analysis_overview": {
      "verdict": "blocked",
      "verdict_label": "Blocked",
      "verdict_reason": "Agent2 output contract buzilgan.",
      "summary_lines": [
        "Compliance score: 0%",
        "REQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi."
      ],
      "section_counts": {
        "completed": 0,
        "failed": 0,
        "issues": 2,
        "figma": 0
      },
      "missing_figma_access": true,
      "requested_sections": [
        "summary",
        "completed",
        "partial",
        "failed",
        "issues",
        "figma"
      ]
    },
    "task_info": {
      "key": "DEV-8144",
      "summary": "Error - Zakaz da product o'chib ketish xatoligi",
      "issue_type": "DEV-ERROR",
      "status": "Closed",
      "assignee": "Nekboyev og'abek",
      "reporter": "Turgunov Jasur",
      "priority": "Medium",
      "story_points": 1,
      "created_at": "2026-04-09",
      "resolved_at": "2026-05-15",
      "labels": [
        "Order_form"
      ],
      "components": []
    },
    "run_info": {
      "source": "manual",
      "requested_output_profile": "ui",
      "comments_enabled": true,
      "max_comments_to_read": 15,
      "smart_patch_enabled": true,
      "ai_data_section_order": [
        "tz",
        "comments",
        "code"
      ],
      "files_analyzed": 4,
      "total_files_changed": 4,
      "prompt_size_chars": 698,
      "ai_retry_count": 0,
      "ai_model": "gemini-2.5-flash",
      "ai_primary_model": "gemini-2.5-flash",
      "ai_fallback_model": "gemini-2.5-flash",
      "ai_used_fallback": false
    },
    "qa_recommendation": {
      "action": "manual_review",
      "label": "Manual review kerak",
      "reason": "Figma evidence cheklangan, dizayn bo'yicha yakuniy qaror uchun qo'shimcha tekshiruv kerak."
    },
    "comment_intelligence": {
      "summary": "Comment yo'q",
      "has_scope_changes": false,
      "change_count": 0,
      "total_comments": 0,
      "filtered_out_ai_comments": 2,
      "has_dev_objections": false,
      "objection_count": 0,
      "deferred_scope_detected": false,
      "scope_note": "Muhim scope o'zgarishi topilmadi.",
      "important_comments": [],
      "deferred_scope_comments": [],
      "dev_objections": []
    },
    "workflow_info": {
      "available": false,
      "source": "manual",
      "task_status": "",
      "service1_status": "",
      "service2_status": "",
      "compliance_score": 0,
      "return_reason": "",
      "blocked_at": "",
      "blocked_retry_at": "",
      "updated_at": "",
      "return_threshold": 70,
      "auto_return_enabled": true,
      "is_recheck": false,
      "note": "Compliance score thresholddan past bo'lsa webhook oqimida auto-return ishlashi mumkin."
    },
    "requirement_matrix": [],
    "effective_settings": {
      "visible_sections": [
        "partial",
        "failed",
        "figma",
        "completed",
        "issues"
      ],
      "read_comments_enabled": true,
      "max_comments_to_read": 15,
      "default_use_smart_patch": true,
      "agent2_parallelism": 5,
      "agent2_batch_size": 6,
      "effective_use_smart_patch": true,
      "ai_data_section_order": [
        "tz",
        "comments",
        "code"
      ],
      "show_contradictory_comments": false,
      "agent1_rules": {
        "figma_scope_enabled": false,
        "coverage_threshold": 1
      },
      "requested_output_profile": "ui"
    },
    "execution_mode": "multi_agent",
    "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
    "run_state": "blocked",
    "agent_runs": [
      {
        "id": 148,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent1_scope_builder",
        "agent_label": "Agent1 Scope Builder",
        "agent_order": 1,
        "state": "completed",
        "primary_model": "gemini-2.5-flash",
        "actual_model": "gemini-2.5-flash",
        "fallback_model": "",
        "used_fallback": false,
        "attempts": 1,
        "confidence": null,
        "input_summary": "tz: 403 belgi. comments: 0 ta. figma: 0 ta.",
        "output_summary": "1 ta requirement ajratildi.",
        "error_text": null,
        "created_at": "2026-05-22T18:32:54.098279+05:00",
        "updated_at": "2026-05-22T18:33:06.771394+05:00",
        "started_at": "2026-05-22T18:33:05.010514+05:00",
        "finished_at": "2026-05-22T18:33:06.765502+05:00",
        "warnings": [],
        "artifact": {
          "summary": "None",
          "requirements": [
            {
              "id": "REQ-1",
              "text": "Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.",
              "source": "tz"
            }
          ],
          "warnings": [],
          "parse_mode": "model_json",
          "parse_metadata": {
            "ok": true,
            "raw_length": 217,
            "used_cleanup": false,
            "used_repair": false,
            "repair_type": "parsed_json",
            "error": null,
            "warnings": []
          },
          "raw_model_excerpt": "{\"requirements\": [{\"id\": \"REQ-1\", \"text\": \"Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.\", \"source\": \"tz\"}]}"
        }
      },
      {
        "id": 149,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent2_verifier",
        "agent_label": "Agent2 Verifier",
        "agent_order": 2,
        "state": "failed",
        "primary_model": "gemini-2.5-pro",
        "actual_model": "gemini-2.5-pro",
        "fallback_model": "gemini-2.5-flash",
        "used_fallback": false,
        "attempts": 1,
        "confidence": null,
        "input_summary": "Verifierga 1 ta requirement yuborildi. Code context: 13656 belgi. Batch size: 6. Parallelism: 1.",
        "output_summary": "1 ta requirement 1 ta batch orqali tekshirildi.",
        "error_text": null,
        "created_at": "2026-05-22T18:32:54.098279+05:00",
        "updated_at": "2026-05-22T18:35:58.261207+05:00",
        "started_at": "2026-05-22T18:33:06.793045+05:00",
        "finished_at": "2026-05-22T18:35:58.256653+05:00",
        "warnings": [
          "Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
        ],
        "artifact": {
          "summary": "",
          "verifications": [
            {
              "id": "REQ-1",
              "status": "failed",
              "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi; manual review kerak: Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
            }
          ],
          "extra": [],
          "technical_failures": [
            {
              "id": "REQ-1",
              "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
              "attempts": [
                {
                  "attempt": 1,
                  "state": "parse_failed",
                  "latency_ms": 64508,
                  "model": "gemini-2.5-pro",
                  "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                  "raw_length": 0,
                  "raw_excerpt": "",
                  "cached_content_token_count": 0,
                  "prompt_token_count": 0,
                  "candidates_token_count": 0,
                  "total_token_count": 0
                },
                {
                  "attempt": 2,
                  "state": "parse_failed",
                  "latency_ms": 53333,
                  "model": "gemini-2.5-pro",
                  "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                  "raw_length": 0,
                  "raw_excerpt": "",
                  "cached_content_token_count": 0,
                  "prompt_token_count": 0,
                  "candidates_token_count": 0,
                  "total_token_count": 0
                }
              ]
            }
          ],
          "checker_coverage": {
            "expected": [
              "REQ-1"
            ],
            "actual": [
              "REQ-1"
            ],
            "missing": [],
            "invalid": []
          },
          "retry_count": 1,
          "verification_mode": "batch",
          "metrics": {
            "mode": "batch",
            "code_context_chars": 13656,
            "requirement_count": 1,
            "agent2_batch_size": 6,
            "batch_count": 1,
            "explicit_cache_enabled": true,
            "explicit_cache_error": "",
            "cached_content_token_count": 4169,
            "prompt_token_count": 4670,
            "candidates_token_count": 9,
            "total_token_count": 6268,
            "parallelism": 1,
            "requirement_verification_count": 1,
            "agent2_call_count": 3,
            "retry_count": 1,
            "schema_validation_failures": 2,
            "technical_failure_count": 1,
            "repair_success_count": 0,
            "cleanup_success_count": 0,
            "empty_response_count": 0,
            "weak_evidence_count": 0,
            "extra_count": 0,
            "extra_scan_state": "completed",
            "missing_verification_count": 0,
            "total_latency_ms": 171412,
            "per_requirement_latency_ms": [
              117979
            ]
          },
          "calls": [
            {
              "id": "REQ-1",
              "state": "technical_failure",
              "latency_ms": 117979,
              "model": "gemini-2.5-pro",
              "attempt_count": 2,
              "attempts": [
                {
                  "attempt": 1,
                  "state": "parse_failed",
                  "latency_ms": 64508,
                  "model": "gemini-2.5-pro",
                  "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                  "raw_length": 0,
                  "raw_excerpt": "",
                  "cached_content_token_count": 0,
                  "prompt_token_count": 0,
                  "candidates_token_count": 0,
                  "total_token_count": 0
                },
                {
                  "attempt": 2,
                  "state": "parse_failed",
                  "latency_ms": 53333,
                  "model": "gemini-2.5-pro",
                  "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                  "raw_length": 0,
                  "raw_excerpt": "",
                  "cached_content_token_count": 0,
                  "prompt_token_count": 0,
                  "candidates_token_count": 0,
                  "total_token_count": 0
                }
              ]
            }
          ],
          "extra_scan": {
            "state": "completed",
            "latency_ms": 51670,
            "attempt_count": 1,
            "attempts": [
              {
                "attempt": 1,
                "state": "completed",
                "latency_ms": 51670,
                "model": "gemini-2.5-pro",
                "raw_length": 17,
                "used_cleanup": false,
                "used_repair": false,
                "repair_type": "parsed_json",
                "warnings": [],
                "extra_count": 0,
                "cached_content_token_count": 4169,
                "prompt_token_count": 4670,
                "candidates_token_count": 9,
                "total_token_count": 6268
              }
            ],
            "extra_count": 0
          },
          "explicit_cache": {
            "enabled": true,
            "error": "",
            "cache_name_present": true,
            "delete_on_finish": true,
            "ttl_seconds": 600
          }
        }
      },
      {
        "id": 150,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent3_arbiter",
        "agent_label": "Agent3 Arbiter",
        "agent_order": 3,
        "state": "failed",
        "primary_model": "gemini-2.5-flash",
        "actual_model": "gemini-2.5-flash",
        "fallback_model": "",
        "used_fallback": false,
        "attempts": 1,
        "confidence": null,
        "input_summary": "Arbiterga 1 ta inventory va 1 ta verification yuborildi.",
        "output_summary": "1 ta requirement bo'yicha checker final matrix hisoblandi.",
        "error_text": null,
        "created_at": "2026-05-22T18:32:54.098279+05:00",
        "updated_at": "2026-05-22T18:36:00.616823+05:00",
        "started_at": "2026-05-22T18:35:59.220462+05:00",
        "finished_at": "2026-05-22T18:36:00.610986+05:00",
        "warnings": [],
        "artifact": {
          "summary": "REQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi.",
          "run_state": "blocked",
          "verdict": "blocked",
          "verdict_label": "Blocked",
          "verdict_reason": "Agent2 output contract buzilgan.",
          "quality_status": "agent2_failed",
          "total_requirements": 1,
          "completed_count": 0,
          "failed_count": 0,
          "technical_count": 1,
          "completed": [],
          "failed": [],
          "technical": [
            "REQ-1"
          ],
          "missing": [],
          "invalid": [],
          "extra": [],
          "extra_code_risk": "none",
          "requirements": [
            {
              "id": "REQ-1",
              "text": "Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.",
              "source": "tz",
              "status": "manual_review",
              "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi; manual review kerak: Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
              "technical_failure": true
            }
          ]
        }
      }
    ],
    "run_events": [
      {
        "id": 458,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "info",
        "event_type": "run_created",
        "message": "Checker run yaratildi",
        "created_at": "2026-05-22T18:32:54.099633+05:00",
        "meta": {
          "execution_mode": "multi_agent",
          "source": "manual"
        }
      },
      {
        "id": 459,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "info",
        "event_type": "run_started",
        "message": "Multi-agent checker run boshlandi",
        "created_at": "2026-05-22T18:32:54.120733+05:00",
        "meta": {}
      },
      {
        "id": 460,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "success",
        "event_type": "input_status",
        "message": "JIRA'dan 2 ta PR topildi",
        "created_at": "2026-05-22T18:32:58.687600+05:00",
        "meta": {}
      },
      {
        "id": 461,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "progress",
        "event_type": "input_status",
        "message": "2 ta PR tahlil qilinmoqda (Smart Patch)...",
        "created_at": "2026-05-22T18:32:58.702359+05:00",
        "meta": {}
      },
      {
        "id": 462,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "info",
        "event_type": "input_status",
        "message": "Merged PR topildi → merged bo'lmagan PR'lar o'tkazib yuborildi: ['#11381']",
        "created_at": "2026-05-22T18:33:04.845298+05:00",
        "meta": {}
      },
      {
        "id": 463,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "success",
        "event_type": "input_status",
        "message": "1 ta PR tahlil qilindi (Smart Patch): 4 fayl, +45/-46",
        "created_at": "2026-05-22T18:33:04.864082+05:00",
        "meta": {}
      },
      {
        "id": 464,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "info",
        "event_type": "input_status",
        "message": "Promptdan 2 ta oldingi AI comment chiqarib tashlandi",
        "created_at": "2026-05-22T18:33:04.962685+05:00",
        "meta": {}
      },
      {
        "id": 465,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "info",
        "event_type": "input_collection_done",
        "message": "Input collection tugadi",
        "created_at": "2026-05-22T18:33:05.005796+05:00",
        "meta": {
          "comments_enabled": true,
          "files_changed": 4,
          "figma_count": 0,
          "agent1_comments": 0,
          "agent1_figma": 0,
          "is_recheck": false
        }
      },
      {
        "id": 466,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent1_scope_builder",
        "level": "info",
        "event_type": "agent_started",
        "message": "TZ, comment va Figma asosida requirement inventory ajratilmoqda",
        "created_at": "2026-05-22T18:33:05.016786+05:00",
        "meta": {
          "state": "running"
        }
      },
      {
        "id": 467,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent1_scope_builder",
        "level": "info",
        "event_type": "agent_finished",
        "message": "1 ta requirement ajratildi.",
        "created_at": "2026-05-22T18:33:06.780897+05:00",
        "meta": {
          "state": "completed",
          "input_summary": "tz: 403 belgi. comments: 0 ta. figma: 0 ta.",
          "output_summary": "1 ta requirement ajratildi.",
          "error_text": "",
          "warnings": [],
          "actual_model": "gemini-2.5-flash",
          "primary_model": "gemini-2.5-flash",
          "fallback_model": "",
          "used_fallback": false,
          "artifact_preview": {
            "keys": [
              "parse_metadata",
              "parse_mode",
              "raw_model_excerpt",
              "requirements",
              "summary",
              "warnings"
            ],
            "summary": "None",
            "parse_mode": "model_json",
            "requirements_total": 1,
            "raw_model_excerpt": "{\"requirements\": [{\"id\": \"REQ-1\", \"text\": \"Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.\", \"source\": \"tz\"}]}"
          }
        }
      },
      {
        "id": 468,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent2_verifier",
        "level": "info",
        "event_type": "agent_started",
        "message": "Requirementlar kod va PR diff bo'yicha tekshirilmoqda",
        "created_at": "2026-05-22T18:33:06.803575+05:00",
        "meta": {
          "state": "running"
        }
      },
      {
        "id": 469,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent2_verifier",
        "level": "error",
        "event_type": "agent_finished",
        "message": "1 ta requirement 1 ta batch orqali tekshirildi.",
        "created_at": "2026-05-22T18:35:58.266242+05:00",
        "meta": {
          "state": "failed",
          "input_summary": "Verifierga 1 ta requirement yuborildi. Code context: 13656 belgi. Batch size: 6. Parallelism: 1.",
          "output_summary": "1 ta requirement 1 ta batch orqali tekshirildi.",
          "error_text": "",
          "warnings": [
            "Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
          ],
          "actual_model": "gemini-2.5-pro",
          "primary_model": "gemini-2.5-pro",
          "fallback_model": "gemini-2.5-flash",
          "used_fallback": false,
          "artifact_preview": {
            "keys": [
              "calls",
              "checker_coverage",
              "explicit_cache",
              "extra",
              "extra_scan",
              "metrics",
              "retry_count",
              "summary",
              "technical_failures",
              "verification_mode",
              "verifications"
            ],
            "verifications_total": 1
          }
        }
      },
      {
        "id": 470,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent3_arbiter",
        "level": "info",
        "event_type": "agent_started",
        "message": "Agent1 va Agent2 natijalari arbitraj qilinmoqda",
        "created_at": "2026-05-22T18:35:59.234287+05:00",
        "meta": {
          "state": "running"
        }
      },
      {
        "id": 471,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": "agent3_arbiter",
        "level": "error",
        "event_type": "agent_finished",
        "message": "1 ta requirement bo'yicha checker final matrix hisoblandi.",
        "created_at": "2026-05-22T18:36:00.625210+05:00",
        "meta": {
          "state": "failed",
          "input_summary": "Arbiterga 1 ta inventory va 1 ta verification yuborildi.",
          "output_summary": "1 ta requirement bo'yicha checker final matrix hisoblandi.",
          "error_text": "",
          "warnings": [],
          "actual_model": "gemini-2.5-flash",
          "primary_model": "gemini-2.5-flash",
          "fallback_model": "",
          "used_fallback": false,
          "artifact_preview": {
            "keys": [
              "completed",
              "completed_count",
              "extra",
              "extra_code_risk",
              "failed",
              "failed_count",
              "invalid",
              "missing",
              "quality_status",
              "requirements",
              "run_state",
              "summary"
            ],
            "summary": "REQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi.",
            "requirements_total": 1
          }
        }
      },
      {
        "id": 472,
        "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
        "agent_key": null,
        "level": "info",
        "event_type": "run_finalizing",
        "message": "Agent natijalari yakuniy resultga yig'ilmoqda",
        "created_at": "2026-05-22T18:36:00.632865+05:00",
        "meta": {
          "requirements_total": 1,
          "effective_requirements_total": 1,
          "verifications_total": 1,
          "requirements_result_total": 1
        }
      }
    ],
    "requirement_inventory": [
      {
        "id": "REQ-1",
        "text": "Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.",
        "source": "tz"
      }
    ],
    "verifications": [
      {
        "id": "REQ-1",
        "status": "failed",
        "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi; manual review kerak: Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
      }
    ],
    "arbiter_summary": {
      "summary": "REQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi.",
      "verdict": "blocked",
      "verdict_label": "Blocked",
      "verdict_reason": "Agent2 output contract buzilgan.",
      "quality_status": "agent2_failed",
      "total_requirements": 1,
      "completed_count": 0,
      "failed_count": 0,
      "technical_count": 1,
      "completed": [],
      "failed": [],
      "technical": [
        "REQ-1"
      ],
      "missing": [],
      "invalid": [],
      "extra": [],
      "extra_code_risk": "none",
      "requirements": [
        {
          "id": "REQ-1",
          "text": "Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.",
          "source": "tz",
          "status": "manual_review",
          "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi; manual review kerak: Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
          "technical_failure": true
        }
      ]
    }
  },
  "agent_runs": [
    {
      "id": 148,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent1_scope_builder",
      "agent_label": "Agent1 Scope Builder",
      "agent_order": 1,
      "state": "completed",
      "primary_model": "gemini-2.5-flash",
      "actual_model": "gemini-2.5-flash",
      "fallback_model": "",
      "used_fallback": false,
      "attempts": 1,
      "confidence": null,
      "input_summary": "tz: 403 belgi. comments: 0 ta. figma: 0 ta.",
      "output_summary": "1 ta requirement ajratildi.",
      "error_text": null,
      "created_at": "2026-05-22T18:32:54.098279+05:00",
      "updated_at": "2026-05-22T18:33:06.771394+05:00",
      "started_at": "2026-05-22T18:33:05.010514+05:00",
      "finished_at": "2026-05-22T18:33:06.765502+05:00",
      "warnings": [],
      "artifact": {
        "summary": "None",
        "requirements": [
          {
            "id": "REQ-1",
            "text": "Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.",
            "source": "tz"
          }
        ],
        "warnings": [],
        "parse_mode": "model_json",
        "parse_metadata": {
          "ok": true,
          "raw_length": 217,
          "used_cleanup": false,
          "used_repair": false,
          "repair_type": "parsed_json",
          "error": null,
          "warnings": []
        },
        "raw_model_excerpt": "{\"requirements\": [{\"id\": \"REQ-1\", \"text\": \"Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.\", \"source\": \"tz\"}]}"
      }
    },
    {
      "id": 149,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent2_verifier",
      "agent_label": "Agent2 Verifier",
      "agent_order": 2,
      "state": "failed",
      "primary_model": "gemini-2.5-pro",
      "actual_model": "gemini-2.5-pro",
      "fallback_model": "gemini-2.5-flash",
      "used_fallback": false,
      "attempts": 1,
      "confidence": null,
      "input_summary": "Verifierga 1 ta requirement yuborildi. Code context: 13656 belgi. Batch size: 6. Parallelism: 1.",
      "output_summary": "1 ta requirement 1 ta batch orqali tekshirildi.",
      "error_text": null,
      "created_at": "2026-05-22T18:32:54.098279+05:00",
      "updated_at": "2026-05-22T18:35:58.261207+05:00",
      "started_at": "2026-05-22T18:33:06.793045+05:00",
      "finished_at": "2026-05-22T18:35:58.256653+05:00",
      "warnings": [
        "Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
      ],
      "artifact": {
        "summary": "",
        "verifications": [
          {
            "id": "REQ-1",
            "status": "failed",
            "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi; manual review kerak: Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
          }
        ],
        "extra": [],
        "technical_failures": [
          {
            "id": "REQ-1",
            "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
            "attempts": [
              {
                "attempt": 1,
                "state": "parse_failed",
                "latency_ms": 64508,
                "model": "gemini-2.5-pro",
                "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                "raw_length": 0,
                "raw_excerpt": "",
                "cached_content_token_count": 0,
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0
              },
              {
                "attempt": 2,
                "state": "parse_failed",
                "latency_ms": 53333,
                "model": "gemini-2.5-pro",
                "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                "raw_length": 0,
                "raw_excerpt": "",
                "cached_content_token_count": 0,
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0
              }
            ]
          }
        ],
        "checker_coverage": {
          "expected": [
            "REQ-1"
          ],
          "actual": [
            "REQ-1"
          ],
          "missing": [],
          "invalid": []
        },
        "retry_count": 1,
        "verification_mode": "batch",
        "metrics": {
          "mode": "batch",
          "code_context_chars": 13656,
          "requirement_count": 1,
          "agent2_batch_size": 6,
          "batch_count": 1,
          "explicit_cache_enabled": true,
          "explicit_cache_error": "",
          "cached_content_token_count": 4169,
          "prompt_token_count": 4670,
          "candidates_token_count": 9,
          "total_token_count": 6268,
          "parallelism": 1,
          "requirement_verification_count": 1,
          "agent2_call_count": 3,
          "retry_count": 1,
          "schema_validation_failures": 2,
          "technical_failure_count": 1,
          "repair_success_count": 0,
          "cleanup_success_count": 0,
          "empty_response_count": 0,
          "weak_evidence_count": 0,
          "extra_count": 0,
          "extra_scan_state": "completed",
          "missing_verification_count": 0,
          "total_latency_ms": 171412,
          "per_requirement_latency_ms": [
            117979
          ]
        },
        "calls": [
          {
            "id": "REQ-1",
            "state": "technical_failure",
            "latency_ms": 117979,
            "model": "gemini-2.5-pro",
            "attempt_count": 2,
            "attempts": [
              {
                "attempt": 1,
                "state": "parse_failed",
                "latency_ms": 64508,
                "model": "gemini-2.5-pro",
                "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                "raw_length": 0,
                "raw_excerpt": "",
                "cached_content_token_count": 0,
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0
              },
              {
                "attempt": 2,
                "state": "parse_failed",
                "latency_ms": 53333,
                "model": "gemini-2.5-pro",
                "error": "Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
                "raw_length": 0,
                "raw_excerpt": "",
                "cached_content_token_count": 0,
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0
              }
            ]
          }
        ],
        "extra_scan": {
          "state": "completed",
          "latency_ms": 51670,
          "attempt_count": 1,
          "attempts": [
            {
              "attempt": 1,
              "state": "completed",
              "latency_ms": 51670,
              "model": "gemini-2.5-pro",
              "raw_length": 17,
              "used_cleanup": false,
              "used_repair": false,
              "repair_type": "parsed_json",
              "warnings": [],
              "extra_count": 0,
              "cached_content_token_count": 4169,
              "prompt_token_count": 4670,
              "candidates_token_count": 9,
              "total_token_count": 6268
            }
          ],
          "extra_count": 0
        },
        "explicit_cache": {
          "enabled": true,
          "error": "",
          "cache_name_present": true,
          "delete_on_finish": true,
          "ttl_seconds": 600
        }
      }
    },
    {
      "id": 150,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent3_arbiter",
      "agent_label": "Agent3 Arbiter",
      "agent_order": 3,
      "state": "failed",
      "primary_model": "gemini-2.5-flash",
      "actual_model": "gemini-2.5-flash",
      "fallback_model": "",
      "used_fallback": false,
      "attempts": 1,
      "confidence": null,
      "input_summary": "Arbiterga 1 ta inventory va 1 ta verification yuborildi.",
      "output_summary": "1 ta requirement bo'yicha checker final matrix hisoblandi.",
      "error_text": null,
      "created_at": "2026-05-22T18:32:54.098279+05:00",
      "updated_at": "2026-05-22T18:36:00.616823+05:00",
      "started_at": "2026-05-22T18:35:59.220462+05:00",
      "finished_at": "2026-05-22T18:36:00.610986+05:00",
      "warnings": [],
      "artifact": {
        "summary": "REQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi.",
        "run_state": "blocked",
        "verdict": "blocked",
        "verdict_label": "Blocked",
        "verdict_reason": "Agent2 output contract buzilgan.",
        "quality_status": "agent2_failed",
        "total_requirements": 1,
        "completed_count": 0,
        "failed_count": 0,
        "technical_count": 1,
        "completed": [],
        "failed": [],
        "technical": [
          "REQ-1"
        ],
        "missing": [],
        "invalid": [],
        "extra": [],
        "extra_code_risk": "none",
        "requirements": [
          {
            "id": "REQ-1",
            "text": "Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.",
            "source": "tz",
            "status": "manual_review",
            "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi; manual review kerak: Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}",
            "technical_failure": true
          }
        ]
      }
    }
  ],
  "run_events": [
    {
      "id": 458,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "info",
      "event_type": "run_created",
      "message": "Checker run yaratildi",
      "created_at": "2026-05-22T18:32:54.099633+05:00",
      "meta": {
        "execution_mode": "multi_agent",
        "source": "manual"
      }
    },
    {
      "id": 459,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "info",
      "event_type": "run_started",
      "message": "Multi-agent checker run boshlandi",
      "created_at": "2026-05-22T18:32:54.120733+05:00",
      "meta": {}
    },
    {
      "id": 460,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "success",
      "event_type": "input_status",
      "message": "JIRA'dan 2 ta PR topildi",
      "created_at": "2026-05-22T18:32:58.687600+05:00",
      "meta": {}
    },
    {
      "id": 461,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "progress",
      "event_type": "input_status",
      "message": "2 ta PR tahlil qilinmoqda (Smart Patch)...",
      "created_at": "2026-05-22T18:32:58.702359+05:00",
      "meta": {}
    },
    {
      "id": 462,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "info",
      "event_type": "input_status",
      "message": "Merged PR topildi → merged bo'lmagan PR'lar o'tkazib yuborildi: ['#11381']",
      "created_at": "2026-05-22T18:33:04.845298+05:00",
      "meta": {}
    },
    {
      "id": 463,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "success",
      "event_type": "input_status",
      "message": "1 ta PR tahlil qilindi (Smart Patch): 4 fayl, +45/-46",
      "created_at": "2026-05-22T18:33:04.864082+05:00",
      "meta": {}
    },
    {
      "id": 464,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "info",
      "event_type": "input_status",
      "message": "Promptdan 2 ta oldingi AI comment chiqarib tashlandi",
      "created_at": "2026-05-22T18:33:04.962685+05:00",
      "meta": {}
    },
    {
      "id": 465,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "info",
      "event_type": "input_collection_done",
      "message": "Input collection tugadi",
      "created_at": "2026-05-22T18:33:05.005796+05:00",
      "meta": {
        "comments_enabled": true,
        "files_changed": 4,
        "figma_count": 0,
        "agent1_comments": 0,
        "agent1_figma": 0,
        "is_recheck": false
      }
    },
    {
      "id": 466,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent1_scope_builder",
      "level": "info",
      "event_type": "agent_started",
      "message": "TZ, comment va Figma asosida requirement inventory ajratilmoqda",
      "created_at": "2026-05-22T18:33:05.016786+05:00",
      "meta": {
        "state": "running"
      }
    },
    {
      "id": 467,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent1_scope_builder",
      "level": "info",
      "event_type": "agent_finished",
      "message": "1 ta requirement ajratildi.",
      "created_at": "2026-05-22T18:33:06.780897+05:00",
      "meta": {
        "state": "completed",
        "input_summary": "tz: 403 belgi. comments: 0 ta. figma: 0 ta.",
        "output_summary": "1 ta requirement ajratildi.",
        "error_text": "",
        "warnings": [],
        "actual_model": "gemini-2.5-flash",
        "primary_model": "gemini-2.5-flash",
        "fallback_model": "",
        "used_fallback": false,
        "artifact_preview": {
          "keys": [
            "parse_metadata",
            "parse_mode",
            "raw_model_excerpt",
            "requirements",
            "summary",
            "warnings"
          ],
          "summary": "None",
          "parse_mode": "model_json",
          "requirements_total": 1,
          "raw_model_excerpt": "{\"requirements\": [{\"id\": \"REQ-1\", \"text\": \"Product tanlanganidan so'ng, valyutasi va narx turi bir xil bo'lgan bir turdagi kontraktlar almashtirilganda tanlangan Productlar o'chib ketmasligi kerak.\", \"source\": \"tz\"}]}"
        }
      }
    },
    {
      "id": 468,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent2_verifier",
      "level": "info",
      "event_type": "agent_started",
      "message": "Requirementlar kod va PR diff bo'yicha tekshirilmoqda",
      "created_at": "2026-05-22T18:33:06.803575+05:00",
      "meta": {
        "state": "running"
      }
    },
    {
      "id": 469,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent2_verifier",
      "level": "error",
      "event_type": "agent_finished",
      "message": "1 ta requirement 1 ta batch orqali tekshirildi.",
      "created_at": "2026-05-22T18:35:58.266242+05:00",
      "meta": {
        "state": "failed",
        "input_summary": "Verifierga 1 ta requirement yuborildi. Code context: 13656 belgi. Batch size: 6. Parallelism: 1.",
        "output_summary": "1 ta requirement 1 ta batch orqali tekshirildi.",
        "error_text": "",
        "warnings": [
          "Agent2 single verification technical failure (REQ-1): Gemini API xatosi (KEY_1): 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
        ],
        "actual_model": "gemini-2.5-pro",
        "primary_model": "gemini-2.5-pro",
        "fallback_model": "gemini-2.5-flash",
        "used_fallback": false,
        "artifact_preview": {
          "keys": [
            "calls",
            "checker_coverage",
            "explicit_cache",
            "extra",
            "extra_scan",
            "metrics",
            "retry_count",
            "summary",
            "technical_failures",
            "verification_mode",
            "verifications"
          ],
          "verifications_total": 1
        }
      }
    },
    {
      "id": 470,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent3_arbiter",
      "level": "info",
      "event_type": "agent_started",
      "message": "Agent1 va Agent2 natijalari arbitraj qilinmoqda",
      "created_at": "2026-05-22T18:35:59.234287+05:00",
      "meta": {
        "state": "running"
      }
    },
    {
      "id": 471,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": "agent3_arbiter",
      "level": "error",
      "event_type": "agent_finished",
      "message": "1 ta requirement bo'yicha checker final matrix hisoblandi.",
      "created_at": "2026-05-22T18:36:00.625210+05:00",
      "meta": {
        "state": "failed",
        "input_summary": "Arbiterga 1 ta inventory va 1 ta verification yuborildi.",
        "output_summary": "1 ta requirement bo'yicha checker final matrix hisoblandi.",
        "error_text": "",
        "warnings": [],
        "actual_model": "gemini-2.5-flash",
        "primary_model": "gemini-2.5-flash",
        "fallback_model": "",
        "used_fallback": false,
        "artifact_preview": {
          "keys": [
            "completed",
            "completed_count",
            "extra",
            "extra_code_risk",
            "failed",
            "failed_count",
            "invalid",
            "missing",
            "quality_status",
            "requirements",
            "run_state",
            "summary"
          ],
          "summary": "REQ-1 tekshirilmadi. Agent2 texnik xato sababli bu requirementni tekshira olmadi. Hech qanday extra itemlar topilmadi.",
          "requirements_total": 1
        }
      }
    },
    {
      "id": 472,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "info",
      "event_type": "run_finalizing",
      "message": "Agent natijalari yakuniy resultga yig'ilmoqda",
      "created_at": "2026-05-22T18:36:00.632865+05:00",
      "meta": {
        "requirements_total": 1,
        "effective_requirements_total": 1,
        "verifications_total": 1,
        "requirements_result_total": 1
      }
    },
    {
      "id": 473,
      "run_id": "tzpr-320fd13b6d7441b39172135634c78887",
      "agent_key": null,
      "level": "warning",
      "event_type": "run_finished",
      "message": "Checker run blocked holatida yakunlandi",
      "created_at": "2026-05-22T18:36:00.725378+05:00",
      "meta": {
        "run_state": "blocked"
      }
    }
  ]
}