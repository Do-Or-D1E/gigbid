import { gql } from 'graphql-tag';
import { Client } from '@elastic/elasticsearch';

export const typeDefs = gql`
  type Listing {
    id: ID!
    reference: String!
    status: String!
    totalCents: Int!
  }

  type Query {
    listing(id: ID!): Listing
    listings(status: String, first: Int = 20, after: String): [Listing!]!
  }

  type Mutation {
    cancelListing(id: ID!): Listing!
  }
`;

export const resolvers = {
  Query: {
    listing: (_p, { id }, ctx) => ctx.loaders.listing.load(id),
    listings: (_p, args, ctx) => ctx.db.listListing(args),
  },
};

const es = new Client({ node: process.env.ES_URL });

export async function searchListings(q, filters = {}) {
  const res = await es.search({
    index: 'listings',
    size: 24,
    query: {
      bool: {
        must: q ? [{ multi_match: { query: q, fields: ['title^3', 'description'], fuzziness: 'AUTO' } }] : [],
        filter: [
          ...(filters.maxPrice ? [{ range: { price: { lte: filters.maxPrice } } }] : []),
          ...(filters.bbox ? [{ geo_bounding_box: { location: filters.bbox } }] : []),
        ],
      },
    },
    aggs: { beds: { terms: { field: 'bedrooms' } } },
  });
  return res.hits.hits.map((h) => ({ id: h._id, ...h._source }));
}
