export type Stock = { size: string; quantity: number };

export type Product = {
  product_id: string;
  name: string;
  garment_type: string;
  description: string;
  colors: string[];
  search_tags: string[];
  image_url: string;
  price: number;
  inventory?: Stock[];
};

export type ChatProduct = {
  product_id: string;
  name: string;
  price: number;
  image_url: string;
  description: string;
  stock_summary?: string | null;
};
