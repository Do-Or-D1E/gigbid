import { auth } from 'express-openid-connect';
import { Body, Controller, Get, Param, Post, UseGuards } from '@nestjs/common';

export const oidc = auth({
  issuerBaseURL: process.env.AUTH0_ISSUER,
  baseURL: process.env.APP_URL,
  clientID: process.env.AUTH0_CLIENT_ID,
  secret: process.env.SESSION_SECRET,
  authRequired: false,
  authorizationParams: { response_type: 'code', scope: 'openid profile email offline_access' },
  afterCallback: async (req, res, session) => {
    await upsertUserFromClaims(session.id_token);
    return session;
  },
});

import { calculateTotal } from '../totals';

describe('calculateTotal', () => {
  it('sums line items and applies a percentage discount', () => {
    const total = calculateTotal([{ cents: 1000, qty: 2 }, { cents: 550, qty: 1 }], { percent: 10 });
    expect(total).toBe(2295);
  });

  it('never returns a negative total', () => {
    expect(calculateTotal([{ cents: 100, qty: 1 }], { percent: 150 })).toBe(0);
  });

  it('throws on a negative quantity', () => {
    expect(() => calculateTotal([{ cents: 100, qty: -1 }], null)).toThrow('quantity');
  });
});

@Controller('appointments')
@UseGuards(AuthGuard)
export class AppointmentController {
  constructor(private readonly service: AppointmentService) {}

  @Get()
  findAll() {
    return this.service.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.service.findOne(id);
  }

  @Post()
  create(@Body() dto: CreateAppointmentDto) {
    return this.service.create(dto);
  }
}
