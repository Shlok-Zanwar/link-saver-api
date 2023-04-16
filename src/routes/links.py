from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Body
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

from ..db.alchemy_models import users_table, links_table, tags_table, link_tag_mapping_table

router = APIRouter()


"""
create table public.links (
  link_id integer primary key not null default nextval('links_link_id_seq'::regclass),
  user_id integer,
  url text,
  titel text,
  description text,
  metadata jsonb,
  is_deleted integer
);

create table public.tags (
  tag_id integer primary key not null default nextval('tags_tag_id_seq'::regclass),
  tag character varying(500),
  user_id integer
);
create unique index tags_tag_id_key on tags using btree (tag_id);

create table public.link_tag_mapping (
  link_id integer,
  tag_id integer
);
"""


class Tags(BaseModel):
    tag_id: int
    tag: str

class LinkAddModel(BaseModel):
    url: str
    title: str
    description: str
    metadata: dict
    link_id: Optional[int] = None
    tags: List[Tags] = []


@router.post("/links/add")
async def add_link(
        link: LinkAddModel,
        request: Request,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        token_payload = verify_token( request.headers.get('Authorization', "") )
        user_id = token_payload['user_id']

        res = links_table(
            user_id=user_id,
            url=link.url,
            title=link.title,
            description=link.description,
            metadata=link.metadata,
            is_deleted=0
        )
        db.add(res)
        db.flush()
        link_id = res.link_id

        for tag in link.tags:
            tag_id = tag.tag_id
            if tag_id is None or tag_id == 0 or not tag_id:
                res = tags_table(
                    tag=tag.tag,
                    user_id=user_id
                )
                db.add(res)
                db.flush()
                tag_id = res.tag_id

            db.add(link_tag_mapping_table(
                link_id=link_id,
                tag_id=tag_id
            ))

        db.commit()
        return {"status": "success", "message": "Link added successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")


@router.post("/links/edit")
async def edit_link(
        link: LinkAddModel,
        request: Request,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        token_payload = verify_token( request.headers.get('Authorization', "") )
        user_id = token_payload['user_id']

        if not link.link_id:
            raise HTTPException(status_code=400, detail="Link id is required.")

        res = db.query(links_table).filter_by(link_id=link.link_id, user_id=user_id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Link not found.")

        res.url = link.url
        res.title = link.title
        res.description = link.description
        res.metadata = link.metadata

        db.query(link_tag_mapping_table).filter_by(link_id=link.link_id).delete()

        for tag in link.tags:
            tag_id = tag.tag_id
            if tag_id is None or tag_id == 0 or not tag_id:
                res = tags_table(
                    tag=tag.tag,
                    user_id=user_id
                )
                db.add(res)
                db.flush()
                tag_id = res.tag_id

            db.add(link_tag_mapping_table(
                link_id=link.link_id,
                tag_id=tag_id
            ))

        db.commit()
        return {"status": "success", "message": "Link updated successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")


@router.get("/links/delete")
def delete_link(
        link_id: int,
        request: Request,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        token_payload = verify_token( request.headers.get('Authorization', "") )
        user_id = token_payload['user_id']

        res = db.query(links_table).filter_by(link_id=link_id, user_id=user_id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Link not found.")

        res.is_deleted = 1
        db.commit()
        return {"status": "success", "message": "Link deleted successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")


class GetLinksModel(BaseModel):
    tags: List[int] = []
@router.post("/links/get")
def get_links(
        request: Request,
        get_links: GetLinksModel,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        token_payload = verify_token( request.headers.get('Authorization', "") )
        user_id = token_payload['user_id']

        cursor = rdb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = f"""
            SELECT * FROM links WHERE user_id = {user_id} AND is_deleted = 0
            AND link_id IN (
                SELECT link_id FROM link_tag_mapping WHERE tag_id IN (
                    SELECT tag_id FROM tags WHERE tag_id IN ({','.join([f"{tag}" for tag in get_links.tags])})
                )
            )
        """
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()

        for link in res:
            cursor = rdb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = f"""
                SELECT * FROM tags WHERE tag_id IN (
                    SELECT tag_id FROM link_tag_mapping WHERE link_id = {link['link_id']}
                )
            """
            cursor.execute(query)
            link['tags'] = cursor.fetchall()
            cursor.close()



        return {"status": "success", "data": res}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")



@router.get("/tags/get")
def get_tags(
        request: Request,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        token_payload = verify_token( request.headers.get('Authorization', "") )
        user_id = token_payload['user_id']

        cursor = rdb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = f"""
            SELECT * FROM tags WHERE user_id = {user_id}
        """
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()

        return {"status": "success", "data": res}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")

# Get link by id for edit
@router.get("/links/get/{link_id}")
def get_link_by_id(
        link_id: int,
        request: Request,
        db: Session = Depends(get_db),
        rdb: Session = Depends(get_raw_db)
):
    try:
        token_payload = verify_token( request.headers.get('Authorization', "") )
        user_id = token_payload['user_id']

        res = db.query(links_table).filter_by(link_id=link_id, user_id=user_id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Link not found.")

        data = res.__dict__

        data['tags'] = []
        cursor = rdb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = f"""
            SELECT tg.tag, tg.tag_id FROM tags tg
            INNER JOIN link_tag_mapping ltm ON ltm.tag_id = tg.tag_id
            WHERE ltm.link_id = {link_id}
        """
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()

        data['tags'] = res

        return {"status": "success", "data": data}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(f"{e}")
        raise HTTPException(status_code=500, detail=f"{e}")




