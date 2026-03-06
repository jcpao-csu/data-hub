# Database Schema

> **Note:** The charge type flags (boolean offense categories) and special designations (dv, blairs_law, valentines_law, ipvi) appear across multiple tables. They always carry the same meaning: TRUE if the defendant was charged with that offense type.

> **Note:** It's worth noting that the `karpel_` tables track unique cases (by row), as the raw data, which tracks unique charges (a criminal case can have more than one charge) has been processed to consolidate tables from charge-level to case-level, for ease of data analysis and visualization. Available data begins from 2016 onwards. Further, because the charge information in `karpel_rcvd` and `karpel_ntfld` have not NECESSARILY been filed with the court, these charges are only referred charges. Whereas, for `karpel_fld` and `karpel_disp`, these charges have been filed with the court, and are thus actual (not just referred/recommended) charges.

---

## 1. `karpel_rcvd`
Criminal cases referred to the prosecuting attorney's office from law enforcement agencies. 

### Identifiers & Case Numbers
| Column | Type | Notes |
|---|---|---|
| pbk_num | VARCHAR | Auto-generated Case Number, unique ID |
| pbk_def_num | VARCHAR | Auto-generated Person Number, unique ID |
| court_num | VARCHAR | Court case number |
| report_num | VARCHAR | Incident report number |

### Defendant Demographics
| Column | Type | Notes |
|---|---|---|
| def_dob | DATE | Defendant date of birth |
| def_race | USER-DEFINED | Enum type |
| def_sex | USER-DEFINED | Enum type |
| def_street_address | VARCHAR | |
| def_street_address2 | VARCHAR | |
| def_city | VARCHAR | |
| def_state | VARCHAR | |
| def_zipcode | VARCHAR | |

### Case Details
| Column | Type | Notes |
|---|---|---|
| arrest_date | DATE | Date of arrest |
| ref_date | DATE | Referral date; IMPORTANT to track unique case referral date |
| custody_status | VARCHAR | Custody status |
| apa | VARCHAR | APA assignment |
| ref_office | VARCHAR | Office location (Downtown, Eastern Jack, or NULL) |
| agency_name | VARCHAR | Referring police agency |

### Lead Charge
| Column | Type | Notes |
|---|---|---|
| rcvd_lead_code | VARCHAR | Lead referred charge code |
| rcvd_lead_desc | TEXT | Lead referred charge description |
| rcvd_lead_sev | VARCHAR | Referred lead charge severity |
| rcvd_lead_class | VARCHAR | Referred lead charge class |
| rcvd_lead_category | VARCHAR | Referred lead charge category |
| rcvd_lead_count | SMALLINT | Charge order number of referred lead charge |
| rcvd_lead_sevclass_rank | NUMERIC | Severity/class rank of referred lead charge |
| rcvd_lead_address | VARCHAR | Address associated with referred lead charge |
| rcvd_lead_address2 | VARCHAR | |
| rcvd_lead_city | VARCHAR | |
| rcvd_lead_state | VARCHAR | |
| rcvd_lead_zipcode | VARCHAR | |

### Special Designations
| Column | Type | Notes |
|---|---|---|
| dv | BOOLEAN | Domestic violence assault charge applicable |
| blairs_law | BOOLEAN | Blair's Law applicable |
| valentines_law | BOOLEAN | Valentine's Law applicable |
| ipvi | BOOLEAN | Intimate partner violence & intimidation flagged |

### Charge Type Flags
*All boolean — TRUE if defendant was charged with this offense type*

| Column | Column | Column | Column |
|---|---|---|---|
| homicide | vehicular_homicide | assault | sexual_assault |
| sex_abuse | robbery | burglary | kidnapping |
| stalking | harassment | drugs | weapons |
| arson | stealing | stealing_vehicle | stolen_property |
| property_damage | fraud | forgery | bribery |
| election_fraud | terrorism | treason | prostitution |
| obscenity | gambling | alcohol | liquor_laws |
| motor_vehicle | family_crime | immigration | health_violation |
| taxation | judicial_offense | conservation | privacy_or_trespass |
| peace_disturbance | ESCAPE | abortion | assorted_other |

---

## 2. `karpel_fld`
Criminal cases with at least one charge formally filed with the court.

### Identifiers & Case Numbers
| Column | Type | Notes |
|---|---|---|
| pbk_num | VARCHAR | Auto-generated Case Number, unique ID |
| court_num | VARCHAR | Court case number |
| report_num | VARCHAR | Incident report number |

### Defendant Demographics
| Column | Type | Notes |
|---|---|---|
| def_dob | DATE | |
| def_race | USER-DEFINED | Enum type |
| def_sex | USER-DEFINED | Enum type |
| def_street_address | VARCHAR | |
| def_street_address2 | VARCHAR | |
| def_city | VARCHAR | |
| def_state | VARCHAR | |
| def_zipcode | VARCHAR | |

### Case Details
| Column | Type | Notes |
|---|---|---|
| ref_date | DATE | Date case was received by the prosecutor's office |
| apa | VARCHAR | APA assignment |
| ref_office | VARCHAR | Office location (Downtown, Eastern Jack, or NULL) |
| agency_name | VARCHAR | Referring police agency |

### Lead Filed Charge
| Column | Type | Notes |
|---|---|---|
| fld_lead_code | VARCHAR | Lead filed charge code |
| fld_lead_desc | TEXT | Lead filed charge description |
| fld_lead_sev | VARCHAR | Lead filed charge severity |
| fld_lead_class | VARCHAR | Lead filed charge class |
| fld_lead_category | VARCHAR | Lead filed charge category |
| fld_lead_count | SMALLINT | Charge order number of referred lead charge |
| fld_lead_sevclass_rank | NUMERIC | Severity/class rank of referred lead charge |
| lead_fld_date | DATE | Date of lead filed charge |
| earliest_fld_date | DATE | Date of earliest filed charge; IMPORTANT to track unique case filing date |
| fld_lead_address | VARCHAR | |
| fld_lead_address2 | VARCHAR | |
| fld_lead_city | VARCHAR | |
| fld_lead_state | VARCHAR | |
| fld_lead_zipcode | VARCHAR | |

### Special Designations
| Column | Type |
|---|---|
| dv | BOOLEAN |
| blairs_law | BOOLEAN |
| valentines_law | BOOLEAN |
| ipvi | BOOLEAN |

### Charge Type Flags
*Same flags as `karpel_rcvd` table — TRUE if charged with offense type*

| Column | Column | Column | Column |
|---|---|---|---|
| homicide | vehicular_homicide | assault | sexual_assault |
| sex_abuse | robbery | burglary | kidnapping |
| stalking | harassment | drugs | weapons |
| arson | stealing | stealing_vehicle | stolen_property |
| property_damage | fraud | forgery | bribery |
| election_fraud | terrorism | treason | prostitution |
| obscenity | gambling | alcohol | liquor_laws |
| motor_vehicle | family_crime | immigration | health_violation |
| taxation | judicial_offense | conservation | privacy_or_trespass |
| peace_disturbance | ESCAPE | abortion | assorted_other |

---

## 3. `karpel_ntfld`
Criminal cases not formally filed. Tracks data of cases' lead, earliest not filed, and minimum (based on the type of outcome--the most optimal outcomes are less, less optimal outcomes are more) referred criminal charges.

### Identifiers & Case Numbers
| Column | Type | Notes |
|---|---|---|
| pbk_num | VARCHAR | Auto-generated Case Number, unique ID |
| report_num | VARCHAR | Incident report number |

### Defendant Demographics
| Column | Type | Notes |
|---|---|---|
| def_dob | DATE | |
| def_race | USER-DEFINED | Enum type |
| def_sex | USER-DEFINED | Enum type |
| def_street_address | VARCHAR | |
| def_street_address2 | VARCHAR | |
| def_city | VARCHAR | |
| def_state | VARCHAR | |
| def_zipcode | VARCHAR | |

### Case Details
| Column | Type | Notes |
|---|---|---|
| ref_date | DATE | Date case was received by the prosecutor's office |
| apa | VARCHAR | APA assignment |
| ref_office | VARCHAR | Office location (Downtown, Eastern Jack, or NULL) |
| agency_name | VARCHAR | Referring police agency |

### Lead Not-Filed Charge
| Column | Type | Notes |
|---|---|---|
| lead_ntfld_code | VARCHAR | |
| lead_ntfld_charge_code | VARCHAR | |
| lead_ntfld_charge_desc | TEXT | |
| lead_ntfld_sev | VARCHAR | |
| lead_ntfld_class | VARCHAR | |
| lead_ntfld_category | VARCHAR | |
| lead_ntfld_charge_category | VARCHAR | |
| lead_ntfld_count | SMALLINT | |
| lead_ntfld_rank | SMALLINT | |
| lead_ntfld_sevclass_rank | NUMERIC | |
| lead_ntfld_date | DATE | |
| lead_ntfld_address | VARCHAR | |
| lead_ntfld_address2 | VARCHAR | |
| lead_ntfld_city | VARCHAR | |
| lead_ntfld_state | VARCHAR | |
| lead_ntfld_zipcode | VARCHAR | |

### Earliest Not-Filed Charge
| Column | Type |
|---|---|
| earliest_ntfld_code | VARCHAR |
| earliest_ntfld_charge_code | VARCHAR |
| earliest_ntfld_charge_desc | TEXT |
| earliest_ntfld_sev | VARCHAR |
| earliest_ntfld_class | VARCHAR |
| earliest_ntfld_category | VARCHAR |
| earliest_ntfld_count | SMALLINT |
| earliest_ntfld_rank | SMALLINT |
| earliest_ntfld_date | DATE |
| earliest_ntfld_city | VARCHAR |
| earliest_ntfld_state | VARCHAR |
| earliest_ntfld_zip | VARCHAR |

### Minimum (based on the type of outcome--the most optimal outcomes are less, less optimal outcomes are more) Not-Filed Charge
| Column | Type |
|---|---|
| min_ntfld_code | VARCHAR |
| min_ntfld_charge_code | VARCHAR |
| min_ntfld_charge_desc | TEXT |
| min_ntfld_sev | VARCHAR |
| min_ntfld_class | VARCHAR |
| min_ntfld_category | VARCHAR |
| min_ntfld_count | SMALLINT |
| min_ntfld_rank | SMALLINT |
| min_ntfld_date | DATE |
| min_ntfld_city | VARCHAR |
| min_ntfld_state | VARCHAR |
| min_ntfld_zip | VARCHAR |

### Special Designations
| Column | Type |
|---|---|
| dv | BOOLEAN |
| blairs_law | BOOLEAN |
| valentines_law | BOOLEAN |
| ipvi | BOOLEAN |

### Charge Type Flags
*Same flags as `karpel_rcvd` table — TRUE if charged with offense type*

| Column | Column | Column | Column |
|---|---|---|---|
| homicide | vehicular_homicide | assault | sexual_assault |
| sex_abuse | robbery | burglary | kidnapping |
| stalking | harassment | drugs | weapons |
| arson | stealing | stealing_vehicle | stolen_property |
| property_damage | fraud | forgery | bribery |
| election_fraud | terrorism | treason | prostitution |
| obscenity | gambling | alcohol | liquor_laws |
| motor_vehicle | family_crime | immigration | health_violation |
| taxation | judicial_offense | conservation | privacy_or_trespass |
| peace_disturbance | ESCAPE | abortion | assorted_other |

---

## 4. `karpel_disp`
Criminal cases disposed, whether by trial, guilty plea (most common), and nolle prosequi, or decision to dismiss. Tracks data of cases' lead, earliest disposed, and minimum (based on the type of outcome--the most optimal outcomes are less, less optimal outcomes are more) criminal charges.

### Identifiers & Case Numbers
| Column | Type | Notes |
|---|---|---|
| pbk_num | VARCHAR | Auto-generated Case Number, unique ID |
| court_num | VARCHAR | Court case number |
| report_num | VARCHAR | Incident report number |

### Defendant Demographics
| Column | Type | Notes |
|---|---|---|
| def_dob | DATE | |
| def_race | USER-DEFINED | Enum type |
| def_sex | USER-DEFINED | Enum type |
| def_street_address | VARCHAR | |
| def_street_address2 | VARCHAR | |
| def_city | VARCHAR | |
| def_state | VARCHAR | |
| def_zipcode | VARCHAR | |

### Case Details
| Column | Type | Notes |
|---|---|---|
| ref_date | DATE | Date case was received by the prosecutor's office |
| apa | VARCHAR | APA assignment |
| ref_office | VARCHAR | Office location (Downtown, Eastern Jack, or NULL) |
| agency_name | VARCHAR | Referring police agency |

### Case-Level Outcome Flags (note: these flags are not mutually exclusive of each other)
| Column | Type | Notes |
|---|---|---|
| any_trial | BOOLEAN | Went to trial on any (at least one) charge |
| any_guilty_verdict | BOOLEAN | Guilty verdict on any charge at trial |
| any_guilty_plea | BOOLEAN | Guilty plea entered on any charge |
| any_dismissed | BOOLEAN | Dismissed/nolle prosequi on any charge |

### Lead Disposition
| Column | Type |
|---|---|
| lead_disp_charge_code | VARCHAR |
| lead_disp_charge_desc | TEXT |
| lead_disp_code | VARCHAR |
| lead_disp_sev | VARCHAR |
| lead_disp_class | VARCHAR |
| lead_disp_category | VARCHAR |
| lead_disp_count | SMALLINT |
| lead_disp_rank | NUMERIC |
| lead_disp_sevclass_rank | NUMERIC |
| lead_disp_date | DATE |
| lead_disp_guilty | BOOLEAN |
| lead_disp_trial | BOOLEAN |
| lead_disp_trial_type | VARCHAR |
| lead_disp_trial_outcome | VARCHAR |
| lead_disp_trial_desc | TEXT |
| lead_disp_plea | BOOLEAN |
| lead_disp_plea_type | VARCHAR |
| lead_disp_plea_category | VARCHAR |
| lead_disp_plea_desc | TEXT |
| lead_disp_nolle | BOOLEAN |
| lead_disp_nolle_rank | NUMERIC |
| lead_disp_nolle_type | VARCHAR |
| lead_disp_nolle_desc | TEXT |
| lead_disp_address | VARCHAR |
| lead_disp_address2 | VARCHAR |
| lead_disp_city | VARCHAR |
| lead_disp_state | VARCHAR |
| lead_disp_zipcode | VARCHAR |

### Earliest Disposition
| Column | Type |
|---|---|
| earliest_disp_charge_code | VARCHAR |
| earliest_disp_charge_desc | TEXT |
| earliest_disp_code | VARCHAR |
| earliest_disp_sev | VARCHAR |
| earliest_disp_class | VARCHAR |
| earliest_disp_category | VARCHAR |
| earliest_disp_count | SMALLINT |
| earliest_disp_rank | NUMERIC |
| earliest_disp_sevclass_rank | NUMERIC |
| earliest_disp_date | DATE |
| earliest_disp_guilty | BOOLEAN |
| earliest_disp_trial | BOOLEAN |
| earliest_disp_trial_type | VARCHAR |
| earliest_disp_trial_outcome | VARCHAR |
| earliest_disp_trial_desc | TEXT |
| earliest_disp_plea | BOOLEAN |
| earliest_disp_plea_type | VARCHAR |
| earliest_disp_plea_category | VARCHAR |
| earliest_disp_plea_desc | TEXT |
| earliest_disp_nolle | BOOLEAN |
| earliest_disp_nolle_rank | NUMERIC |
| earliest_disp_nolle_type | VARCHAR |
| earliest_disp_nolle_desc | TEXT |
| earliest_disp_city | VARCHAR |
| earliest_disp_state | VARCHAR |
| earliest_disp_zip | VARCHAR |

### Minimum Disposition (based on the type of outcome--the most optimal outcomes are less, less optimal outcomes are more)
| Column | Type |
|---|---|
| min_disp_charge_code | VARCHAR |
| min_disp_charge_desc | TEXT |
| min_disp_code | VARCHAR |
| min_disp_sev | VARCHAR |
| min_disp_class | VARCHAR |
| min_disp_category | VARCHAR |
| min_disp_count | SMALLINT |
| min_disp_rank | NUMERIC |
| min_disp_sevclass_rank | NUMERIC |
| min_disp_date | DATE |
| min_disp_guilty | BOOLEAN |
| min_disp_trial | BOOLEAN |
| min_disp_trial_type | VARCHAR |
| min_disp_trial_outcome | VARCHAR |
| min_disp_trial_desc | TEXT |
| min_disp_plea | BOOLEAN |
| min_disp_plea_type | VARCHAR |
| min_disp_plea_category | VARCHAR |
| min_disp_plea_desc | TEXT |
| min_disp_nolle | BOOLEAN |
| min_disp_nolle_rank | NUMERIC |
| min_disp_nolle_type | VARCHAR |
| min_disp_nolle_desc | TEXT |
| min_disp_city | VARCHAR |
| min_disp_state | VARCHAR |
| min_disp_zip | VARCHAR |

### Special Designations
| Column | Type |
|---|---|
| dv | BOOLEAN |
| blairs_law | BOOLEAN |
| valentines_law | BOOLEAN |
| ipvi | BOOLEAN |

### Charge Type Flags
*Same flags as `karpel_rcvd` table — TRUE if charged with offense type*

| Column | Column | Column | Column |
|---|---|---|---|
| homicide | vehicular_homicide | assault | sexual_assault |
| sex_abuse | robbery | burglary | kidnapping |
| stalking | harassment | drugs | weapons |
| arson | stealing | stealing_vehicle | stolen_property |
| property_damage | fraud | forgery | bribery |
| election_fraud | terrorism | treason | prostitution |
| obscenity | gambling | alcohol | liquor_laws |
| motor_vehicle | family_crime | immigration | health_violation |
| taxation | judicial_offense | conservation | privacy_or_trespass |
| peace_disturbance | ESCAPE | abortion | assorted_other |

---

## 5. `agencies`
Lookup table for law enforcement and referral agencies.

| Column | Type | Notes |
|---|---|---|
| agency_id | INTEGER | Primary key |
| full_name | VARCHAR | Full agency name |
| abbr_name | VARCHAR | Abbreviated name |
| karpel_name | VARCHAR | Name as it appears in Karpel system |
| rcvd | VARCHAR | Name as it appears in received records |
| category | VARCHAR | Agency category/type |
| county | VARCHAR | County the agency serves |
| state | VARCHAR | State |
| office_location | VARCHAR | Which office location agencies' cases get referred to (e.g., Downtown, Eastern Jack) |
| street_address | VARCHAR | Physical street address |
| link | TEXT | Website or reference URL |

---

## 6. `mshp_charge_codes`
Missouri State Highway Patrol charge code reference table — maps charge codes to descriptions, severity, categories, and offense flags.

### Identifiers & Classification
| Column | Type | Notes |
|---|---|---|
| charge_code | VARCHAR | Missouri charge code statute |
| mshp_code | VARCHAR | MSHP-specific code |
| ncic_code | VARCHAR | National Crime Information Center code |
| jcpao_ncic | VARCHAR | JCPAO NCIC mapping |
| statute | VARCHAR | Missouri statute reference |
| osca_type | VARCHAR | OSCA offense type |

### Descriptions
| Column | Type | Notes |
|---|---|---|
| short_desc | VARCHAR | Short charge description |
| long_desc | TEXT | Full charge description |

### Severity & Classification
| Column | Type | Notes |
|---|---|---|
| severity | VARCHAR | Charge severity (e.g. Felony, Misdemeanor) |
| class | VARCHAR | Charge class (e.g. A, B, C) |
| sevclass_value | INTEGER | Numeric ranking of severity/class combination |

### Categories
| Column | Type | Notes |
|---|---|---|
| ncic_category | VARCHAR | NCIC offense category |
| jcpao_category | VARCHAR | JCPAO internal category |

### Flags
| Column | Type | Notes |
|---|---|---|
| dv | BOOLEAN | Domestic violence charge |
| harassment | BOOLEAN | Harassment charge |
| stalking | BOOLEAN | Stalking charge |
| already_exists | BOOLEAN | Code already exists in system |
| legacy | BOOLEAN | Legacy/deprecated code |

---

## 7. `fsd_admin`
Monthly Family Support Division administrative caseload summary.

| Column | Type | Notes |
|---|---|---|
| MonthYr | DATE | Month and year of the record |
| New Cases Received/Opened | SMALLINT | Count of new cases opened that month |

---

## 8. `fsd_admin_enf`
Monthly FSD administrative enforcement metrics.

| Column | Type | Notes |
|---|---|---|
| MonthYr | DATE | Month and year of the record |
| Income Withholding Orders | INTEGER | Number of income withholding orders issued |
| Collection | NUMERIC | Dollar amount collected |
| Percentage of Cases Paying | NUMERIC | % of active cases making payments |

---

## 9. `fsd_admin_est`
Monthly FSD administrative establishment metrics — paternity and support order establishment.

| Column | Type | Notes |
|---|---|---|
| MonthYr | DATE | Month and year of the record |
| BOWs Established (# Of Children) | INTEGER | Births out of wedlock — number of children with established orders |
| Notice and Findings (Goal 100) | INTEGER | Notices and findings issued (goal: 100/month) |
| Genetic Testing Results (Goal 100) | INTEGER | Genetic testing results processed (goal: 100/month) |
| Administrative Orders | INTEGER | Number of administrative orders established |

---

## 10. `fsd_judicial_enf`
Monthly FSD judicial enforcement metrics — referrals, collections, and criminal filings.

| Column | Type | Notes |
|---|---|---|
| MonthYr | DATE | Month and year of the record |
| New Referrals | INTEGER | New cases referred to judicial enforcement |
| Collection | NUMERIC | Dollar amount collected |
| Civil Contempts Filed | INTEGER | Civil contempt actions filed |
| Misdemeanors Filed | INTEGER | Misdemeanor charges filed |
| Misdemeanor Convictions | INTEGER | Misdemeanor convictions obtained |
| Felonies Filed | INTEGER | Felony charges filed |
| Felony Convictions | INTEGER | Felony convictions obtained |
| Percentage of Cases Paying | NUMERIC | % of active cases making payments |

---

## 11. `fsd_judicial_pat`
Monthly FSD judicial paternity metrics.

| Column | Type | Notes |
|---|---|---|
| MonthYr | DATE | Month and year of the record |
| New Referrals | INTEGER | New paternity cases referred to judicial |
| BOWs Established (# Of Children) | INTEGER | Births out of wedlock — children with judicially established orders |
| Judicial Orders (095-34 Only) | INTEGER | Judicial orders entered under case type 095-34 |

---

## Enum Types

PostgreSQL custom enum types used across tables. `USER-DEFINED` columns in the schema reference these.

### `karpel_race`
Used for `def_race` in `karpel_rcvd`, `karpel_fld`, `karpel_ntfld`, `karpel_disp`.

| Value | Meaning |
|---|---|
| W | White |
| B | Black |
| H | Hispanic |
| A | Asian |
| I | American Indian |
| M | Multiracial |
| P | Pacific Islander |
| U | Unknown |

### `karpel_sex`
Used for `def_sex` in `karpel_rcvd`, `karpel_fld`, `karpel_ntfld`, `karpel_disp`.

| Value | Meaning |
|---|---|
| M | Male |
| F | Female |
| O | Other |
| U | Unknown |

### `race_enum`
General race enum used in staff/user tables.

| Value | Meaning |
|---|---|
| W | White |
| B | Black |
| H | Hispanic |
| A | Asian |
| AIAN | American Indian or Alaska Native |
| NHPI | Native Hawaiian or Pacific Islander |
| O | Other |

### `sex_enum`
General sex enum used in staff/user tables.

| Value | Meaning |
|---|---|
| M | Male |
| F | Female |
| O | Other |

### `case_status_enum`
Tracks the stage of a case through the system.

| Value | Meaning |
|---|---|
| Received | Arrest received from law enforcement — `karpel_rcvd` |
| Filed | Charges formally filed with the court — `karpel_fld` |
| Not Filed | Referred but not filed — `karpel_ntfld` |
| Disposed | Case has a final outcome — `karpel_disp` |

### `position_enum`
Staff position/role types.

| Value | Meaning |
|---|---|
| APA | Assistant Prosecuting Attorney |
| CTA | Chief Trial Attorney |
| TTL | Trial Team Leader |
| Exec | Executive |
| I | Investigator |
| VA | Victim Advocate |
| LA | Legal Assistant |
| SS | Support Staff |
| INTERN | Intern |
| WARRANT | Warrant division |
| TEST-IGNORE | Test account — exclude from metrics |

### `unit_enum`
Office units/divisions.

| Value | Meaning |
|---|---|
| GCU | General Crimes Unit |
| SVU | Special Victims Unit |
| VCU | Violent Crimes Unit |
| CSU | Community Safety Unit |
| COMBAT | COMBAT drug unit |
| Drug | Drug unit |
| FSD | Family Support Division |
| WARRANT | Warrant division |
| Exec | Executive |

### `location_enum`
Office locations.

| Value | Meaning |
|---|---|
| Dt-11 | Downtown — 11th floor |
| Dt-10 | Downtown — 10th floor |
| Dt-9 | Downtown — 9th floor |
| Dt-7M | Downtown — 7th floor Mezzanine |
| Indy | Independence office |
| FSD | Family Support Division |

### `jd_class_enum`
Law school year classification (for intern/JD tracking).

| Value | Meaning |
|---|---|
| 0L | Pre-law |
| 1L | First year law student |
| 2L | Second year law student |
| 3L | Third year law student |
| Graduated | Law school graduate |
| Other | Other |

### `user_activity_enum`
Audit log event types for user activity tracking.

| Value |
|---|
| SIGN UP |
| LOGIN |
| RESET PASSWORD |
| UPDATE PROFILE |
| UPDATE PHOTO |
| UPDATE NAME |
| UPDATE JOB |
| UPDATE OFFICE |
| UPDATE DEMOGRAPHIC |
| UPDATE INTERN |
| REMOVE PROFILE |
| ANNOUNCEMENT |
| POST-TRIAL SURVEY |
| ADMIN-AUTHORIZE |
| ADMIN-RESET PASSWORD |
| ADMIN-REMOVE PROFILE |
