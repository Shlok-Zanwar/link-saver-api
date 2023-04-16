from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from src.utils.jwt_utils import generate_token, verify_token
import psycopg2.extras
import random
from email.message import EmailMessage
from os import getenv
import smtplib, ssl
from pydantic import BaseModel
from . import get_db, get_raw_db
from loguru import logger

from ..db.alchemy_models import users_table

router = APIRouter()


# create table public.users (
#   user_id integer primary key not null default nextval('users_user_id_seq'::regclass),
#   email character varying(100),
#   password character varying(100),
#   otp integer,
#   is_verified integer,
#   is_deleted integer
# );
#

myEmailId = getenv("EMAIL_ID")
myEmailPassword = getenv("EMAIL_PASSWORD")


def sendMail(message):
    smtp_server = "smtp.gmail.com"
    port = 587  # For starttls
    message['From'] = myEmailId

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.ehlo()  # Can be omitted
        server.starttls(context=context)  # Secure the connection
        server.ehlo()  # Can be omitted
        server.login(myEmailId, myEmailPassword)

        server.send_message(message)
        server.quit()

    except Exception as e:
        # Print any error messages to stdout
        print(e)
        raise HTTPException(status_code=503, detail=f"Unable to send OTP.")


def sendOtp(email, purpose="register"):
    otp = random.randint(100000, 999999)
    if purpose == "register":
        message = f"OTP to login  is " + str(otp) + " ."
    elif purpose == "reset":
        message = f"OTP to reset password is " + str(otp) + " ."
    else:
        message = f"OTP is " + str(otp) + " ."

    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = 'Your OTP'
    msg['To'] = email

    sendMail(msg)
    return otp


class LoginModel(BaseModel):
    email: str
    password: str
    otp: Optional[int] = None
    verify_account: Optional[bool] = False
    reset_password: Optional[bool] = False


@router.post('/login', tags=["User / Login"])
def auth_route(
        data: LoginModel,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        res = db.query(users_table).filter_by(email=data.email, password=data.password, is_deleted=0,
                                              is_verified=1).all()
        if len(res) == 0:
            new_user_chcek = db.query(users_table).filter_by(email=data.email).all()
            if len(new_user_chcek) == 0:
                db.add(users_table(
                    email=data.email,
                    password=data.password,
                    otp=sendOtp(data.email),
                    is_verified=0,
                    is_deleted=0
                ))
                db.commit()
                raise HTTPException(status_code=401, detail=f"Account not verified!")

            if data.verify_account or data.reset_password:
                # Getting the OTP
                res = db.query(users_table).filter_by(email=data.email).all()
                if len(res) == 0:
                    raise HTTPException(status_code=404, detail=f"Email not found!")
                else:
                    otp = res[0].otp

                if otp == data.otp:
                    db.query(users_table).filter_by(email=data.email).update({
                        # "is_deleted": 0,
                        "is_verified": 1,
                        "email": data.email,
                        "password": data.password,
                        "otp": random.randint(100000, 999999)
                    })
                    db.commit()
                    return {"data": {"message": "Account verified successfully."}}
                else:
                    raise HTTPException(status_code=401, detail=f"Invalid OTP!")
            else:
                raise HTTPException(status_code=401, detail=f"Invalid credentials!")
        else:
            token = generate_token({
                "user_id": res[0].user_id,
                "email": res[0].email,
                "is_verified": res[0].is_verified,
                "is_deleted": res[0].is_deleted,
            })
            return {"token": token}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")


class RequestResetModel(BaseModel):
    email: str

@router.post('/request-reset-password', tags=["User / Login"])
def request_reset_password_route(
        data: RequestResetModel,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        res = db.query(users_table).filter_by(email=data.email, is_deleted=0).all()
        if len(res) == 0:
            raise HTTPException(status_code=404, detail=f"Email not found!")

        db.query(users_table).filter_by(email=data.email).update({
            "otp": sendOtp(data.email, "reset")
        })
        db.commit()
        return {"data": {"message": "OTP sent successfully."}}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")
