// shop.sql, written as a Drizzle ORM schema (drizzle-orm/pg-core): keys named
// for JavaScript, columns named for SQL. Drizzle states CHECK constraints; the
// row-level security of shop.sql is not here (this file declares no pgPolicy).
import { sql } from "drizzle-orm";
import {
  bigint, boolean, char, check, date, integer, jsonb, pgEnum, pgTable, primaryKey,
  text, timestamp, uniqueIndex, uuid, varchar,
} from "drizzle-orm/pg-core";
import { authUsers } from "drizzle-orm/supabase";

export const productStatus = pgEnum("product_status", ["draft", "active", "archived"]);
export const orderStatus = pgEnum("order_status", [
  "pending", "paid", "shipped", "delivered", "cancelled", "refunded",
]);

export const categories = pgTable("categories", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: varchar("name", { length: 80 }).notNull().unique(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const products = pgTable("products", {
  id: uuid("id").primaryKey().defaultRandom(),
  title: varchar("title", { length: 120 }).notNull(),
  slug: text("slug").notNull(),
  priceCents: integer("price_cents").notNull(),
  currency: char("currency", { length: 3 }).notNull().default("USD"),
  status: productStatus("status").notNull().default("draft"),
  categoryId: uuid("category_id").references(() => categories.id, { onDelete: "set null" }),
  coverImageUrl: text("cover_image_url"),
  metadata: jsonb("metadata").notNull().default({}),
  isFeatured: boolean("is_featured").notNull().default(false),
  availableOn: date("available_on"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => [
  uniqueIndex("products_slug_key").on(t.slug),
  check("products_price_cents_check", sql`${t.priceCents} >= 0`),
]);

export const tags = pgTable("tags", {
  id: bigint("id", { mode: "number" }).primaryKey().generatedByDefaultAsIdentity(),
  name: varchar("name", { length: 40 }).notNull().unique(),
});

export const productTags = pgTable("product_tags", {
  productId: uuid("product_id").notNull().references(() => products.id, { onDelete: "cascade" }),
  tagId: bigint("tag_id", { mode: "number" }).notNull().references(() => tags.id, { onDelete: "cascade" }),
}, (t) => [primaryKey({ columns: [t.productId, t.tagId] })]);

export const customers = pgTable("customers", {
  id: uuid("id").primaryKey().references(() => authUsers.id, { onDelete: "cascade" }),
  email: text("email").notNull().unique(),
  fullName: varchar("full_name", { length: 120 }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const orders = pgTable("orders", {
  id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
  customerId: uuid("customer_id").notNull().references(() => customers.id, { onDelete: "cascade" }),
  status: orderStatus("status").notNull().default("pending"),
  totalCents: integer("total_cents").notNull(),
  placedAt: timestamp("placed_at").notNull().defaultNow(),
  notes: text("notes"),
}, (t) => [
  check("orders_total_cents_check", sql`${t.totalCents} >= 0`),
  check("orders_notes_check", sql`char_length(${t.notes}) <= 500`),
]);

export const orderItems = pgTable("order_items", {
  id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
  orderId: bigint("order_id", { mode: "number" }).notNull().references(() => orders.id, { onDelete: "cascade" }),
  productId: uuid("product_id").notNull().references(() => products.id),
  quantity: integer("quantity").notNull(),
  unitPriceCents: integer("unit_price_cents").notNull(),
}, (t) => [
  check("order_items_quantity_check", sql`${t.quantity} between 1 and 99`),
  check("order_items_unit_price_cents_check", sql`${t.unitPriceCents} >= 0`),
]);
