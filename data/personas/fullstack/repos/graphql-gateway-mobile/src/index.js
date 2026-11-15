import jwt from 'jsonwebtoken';
import { gql } from 'graphql-tag';

const ACCESS_TTL = '15m';

export function signAccess(userId, role) {
  return jwt.sign({ sub: userId, role }, process.env.JWT_SECRET, { expiresIn: ACCESS_TTL });
}

export function requireAuth(req, res, next) {
  const header = req.headers.authorization ?? '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return res.status(401).json({ error: 'missing token' });
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    return next();
  } catch {
    return res.status(401).json({ error: 'invalid or expired token' });
  }
}

export const typeDefs = gql`
  type Transaction {
    id: ID!
    reference: String!
    status: String!
    totalCents: Int!
  }

  type Query {
    transaction(id: ID!): Transaction
    transactions(status: String, first: Int = 20, after: String): [Transaction!]!
  }

  type Mutation {
    cancelTransaction(id: ID!): Transaction!
  }
`;

export const resolvers = {
  Query: {
    transaction: (_p, { id }, ctx) => ctx.loaders.transaction.load(id),
    transactions: (_p, args, ctx) => ctx.db.listTransaction(args),
  },
};
