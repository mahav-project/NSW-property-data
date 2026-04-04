CREATE TABLE IF NOT EXISTS nsw_property_sales_raw (
    id          SERIAL PRIMARY KEY,
    row_number  INTEGER         NOT NULL,
    raw_line    TEXT            NOT NULL,
    source_file TEXT            NOT NULL,
    ingested_at TIMESTAMP       NOT NULL
);
create or replace
view public.vw_nsw_property_sales as

with deduped as (
select
	distinct
        row_number,
	source_file,
	raw_line
from
	nsw_property_sales_raw
),

parsed as (
select
	row_number,
	source_file,
	raw_line,
	string_to_array(raw_line, ';') as f,
	length(raw_line) - length(replace(raw_line, ';', '')) as sc
from
	deduped
),

mapped as (
select
	row_number,
	source_file,
	-- Format flag
        case
		when sc >= 24 then 'current_2001_to_present'
		else 'archived_1990_to_2001'
	end as file_format,
	sc,
	-- Core identifiers
	f[2] as district_code,
	case
		when sc >= 24 then nullif(f[3], '')
		else nullif(f[5], '')
	end as property_id,
	case
		when sc >= 24 then nullif(f[4], '')
		else null
	end as sale_counter,
	-- Property & address components
        case
		when sc >= 24 then nullif(f[6], '')
		else null
	end as property_name,
	case
		when sc >= 24 then nullif(f[7], '')
		else nullif(f[6], '')
	end as unit_number,
	case
		when sc >= 24 then nullif(f[8], '')
		else nullif(f[7], '')
	end as house_number,
	case
		when sc >= 24 then nullif(f[9], '')
		else nullif(f[8], '')
	end as street_name,
	case
		when sc >= 24 then nullif(f[10], '')
		else nullif(f[9], '')
	end as suburb,
	case
		when sc >= 24 then nullif(f[11], '')
		else nullif(f[10], '')
	end as post_code,
	-- Dates (raw strings for conversion below)
        case
		when sc >= 24 then nullif(f[14], '')
		else nullif(f[11], '')
	end as contract_date_raw,
	case
		when sc >= 24 then nullif(f[15], '')
		else null
	end as settlement_date_raw,
	-- Financials
        case
		when sc >= 24 then nullif(f[16], '')::numeric
		else nullif(f[12], '')::numeric
	end as purchase_price,
	-- Land / area
        case
		when sc < 24 then nullif(f[13], '')
		else null
	end as land_description,
	case
		when sc >= 24 then nullif(f[12], '')::numeric
		else nullif(f[14], '')::numeric
	end as area,
	case
		when sc >= 24 then nullif(f[13], '')
		else nullif(f[15], '')
	end as area_type,
	case
		when sc < 24 then nullif(f[16], '')
		else null
	end as dimensions,
	-- Classification
        case
		when sc >= 24 then nullif(f[17], '')
		else nullif(f[18], '')
	end as zone_code,
	case
		when sc >= 24 then nullif(f[18], '')
		else null
	end as nature_of_property,
	case
		when sc >= 24 then nullif(f[19], '')
		else null
	end as primary_purpose,
	case
		when sc >= 24 then nullif(f[20], '')
		else null
	end as strata_lot_number,
	-- Sale details
        case
		when sc >= 24 then nullif(f[22], '')
		else null
	end as sale_code,
	case
		when sc >= 24
            then case
			when f[23] = '' then 100
			else f[23]::integer
		end
		else null::integer
	end as percent_interest_of_sale,
	case
		when sc >= 24 then nullif(f[24], '')
		else null
	end as dealing_number
from
	parsed
)

select
	row_number,
	source_file,
	file_format,
	-- Identifiers
	district_code,
	property_id,
	sale_counter,
	-- Address components
	property_name,
	unit_number,
	house_number,
	street_name,
	suburb,
	post_code,
	-- Full address  (e.g. "Unit 3, 82 Tamworth St, Abermain NSW 2326")
	trim(both ' ' from concat_ws(', ',
        case when unit_number is not null then 'Unit ' || unit_number end,
        case
            when house_number is not null and street_name is not null
                then house_number || ' ' || street_name
            when street_name is not null
                then street_name
        end,
        case
            when suburb is not null and post_code is not null
                then suburb || ' NSW ' || post_code
            when suburb is not null
                then suburb
        end
    )) as full_address,
	-- Dates as proper DATE type  (source format DD/MM/YYYY)
	  case
		when sc >= 24 then to_date(contract_date_raw, 'YYYYMMDD')
		else to_date(contract_date_raw, 'DD/MM/YYYY')
	end as contract_date,
	extract(year from case
		when sc >= 24 then to_date(contract_date_raw, 'YYYYMMDD')
		else to_date(contract_date_raw, 'DD/MM/YYYY')
	end)::int as contract_year,
	to_date(settlement_date_raw, 'YYYYMMDD') as settlement_date,
	extract(year from to_date(settlement_date_raw, 'YYYYMMDD'))::int as settlement_year,
	-- Financials & land
	purchase_price,
	land_description,
	area,
	area_type,
	dimensions,
	-- Classification
	zone_code,
	nature_of_property,
	primary_purpose,
	strata_lot_number,
	-- Sale details
	sale_code,
	percent_interest_of_sale,
	dealing_number
from
	mapped;
CREATE MATERIALIZED VIEW mv_nsw_property_sales AS
SELECT *
FROM vw_nsw_property_sales;