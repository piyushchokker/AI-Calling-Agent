-- 1. Add owner_id to companies
ALTER TABLE companies ADD COLUMN owner_id uuid REFERENCES auth.users(id) DEFAULT auth.uid();

-- Make owner_id required for all future inserts
-- ALTER TABLE companies ALTER COLUMN owner_id SET NOT NULL; -- (Optional, uncomment if all existing rows have owner_id)

-- 2. Enable Row Level Security (RLS) on all tables
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

-- 3. Create Policies for companies (Owner can read/write their own company)
CREATE POLICY "Companies are isolated by owner_id" ON companies
  FOR ALL
  USING (owner_id = auth.uid())
  WITH CHECK (owner_id = auth.uid());

-- 4. Create Policies for customers (Owner can read/write customers belonging to their company)
CREATE POLICY "Customers are isolated by company owner" ON customers
  FOR ALL
  USING (company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid()))
  WITH CHECK (company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid()));

-- 5. Create Policies for campaigns
CREATE POLICY "Campaigns are isolated by company owner" ON campaigns
  FOR ALL
  USING (company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid()))
  WITH CHECK (company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid()));

-- 6. Create Policies for call_logs
CREATE POLICY "Call logs are isolated by company owner" ON call_logs
  FOR ALL
  USING (customer_id IN (SELECT id FROM customers WHERE company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid())))
  WITH CHECK (customer_id IN (SELECT id FROM customers WHERE company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid())));

-- 7. Webhook events (Only Service Role should access, no public access)
-- No policies means default deny all for authenticated/anon users, which is perfect.
